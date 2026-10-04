import os
import time

from celery import Celery
from celery.signals import task_postrun, task_prerun, worker_ready
from kombu import Exchange, Queue
from prometheus_client import start_http_server

from infrastructure.observability.bootstrap import configure_observability
from infrastructure.observability.metrics import ingestion_stage_duration_seconds

configure_observability(service_name="kip-worker")

app = Celery("ingestion", broker=os.environ.get("RABBITMQ_URL", "amqp://kip:kip@localhost:5673//"))

_dead_letter_exchange = Exchange("ingestion.dlx", type="direct")
_dead_letter_queue = Queue("ingestion.dead_letter", exchange=_dead_letter_exchange, routing_key="dead_letter")

_main_exchange = Exchange("ingestion", type="direct")
_main_queue = Queue(
    "ingestion",
    exchange=_main_exchange,
    routing_key="ingestion",
    queue_arguments={
        "x-dead-letter-exchange": "ingestion.dlx",
        "x-dead-letter-routing-key": "dead_letter",
    },
)

app.conf.task_queues = (_main_queue, _dead_letter_queue)
app.conf.task_default_queue = "ingestion"
app.conf.task_default_exchange = "ingestion"
app.conf.task_default_routing_key = "ingestion"
app.conf.imports = ("presentation.tasks.ingestion",)

_task_start_times: dict[str, float] = {}


@worker_ready.connect
def _start_metrics_server(sender: object = None, **kwargs: object) -> None:
    # worker_ready only fires inside an actual running `celery worker` process,
    # never when this module is merely imported (e.g. by the API, which imports
    # `worker.app` transitively via presentation/tasks/ingestion.py to call
    # .delay()) — importing must never bind a port, only actually running as a
    # worker should.
    start_http_server(int(os.environ.get("METRICS_PORT", "9001")))


@task_prerun.connect
def _record_task_start(
    sender: object = None, task_id: str | None = None, task: object = None, **kwargs: object
) -> None:
    if task_id is not None:
        _task_start_times[task_id] = time.monotonic()


@task_postrun.connect
def _record_task_duration(
    sender: object = None, task_id: str | None = None, task: object = None, **kwargs: object
) -> None:
    if task_id is None:
        return
    start = _task_start_times.pop(task_id, None)
    if start is not None and task is not None:
        ingestion_stage_duration_seconds.labels(stage=task.name).observe(time.monotonic() - start)  # type: ignore[attr-defined]
