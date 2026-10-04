from celery import Celery

import worker  # noqa: F401 — ensures worker.py's Celery signal handlers are connected
from infrastructure.observability.metrics import ingestion_stage_duration_seconds


def _observation_count(stage: str) -> float:
    child = ingestion_stage_duration_seconds.labels(stage=stage)
    return next(s.value for s in child._child_samples() if s.name == "_count")


def test_a_task_execution_records_its_duration() -> None:
    app = Celery("test-app-metrics")
    app.conf.task_always_eager = True

    @app.task(name="metrics_test_task")
    def noop() -> None:
        pass

    count_before = _observation_count("metrics_test_task")
    noop.delay()
    count_after = _observation_count("metrics_test_task")

    assert count_after == count_before + 1
