from celery import Celery

from app.config import settings

celery_app = Celery(
    "tenderproof",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.compile_schema",
        "app.tasks.extract_bidder",
        "app.tasks.evaluate_bidder",
        "app.tasks.finalize_report",
    ],
)

celery_app.conf.update(
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
)
