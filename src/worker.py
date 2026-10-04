import os

from celery import Celery
from kombu import Exchange, Queue

from infrastructure.observability.bootstrap import configure_observability

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
