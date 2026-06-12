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
    # PURGE POINT 2 — unacknowledged message dropped on cold shutdown:
    # `task_acks_late=True` means a task message is NOT acknowledged to the
    # broker until the task completes (success or failure). This protects
    # against worker *crashes* — the broker re-queues the unacknowledged
    # message automatically.
    #
    # However, on a COLD shutdown (triggered by SIGINT / Ctrl+C), Celery
    # explicitly revokes in-flight tasks before dying. Because the revoke
    # happens inside the worker process, Celery acks (or discards) the message
    # itself — bypassing the late-ack safety net. The task is gone.
    #
    # TO PREVENT THIS — add the line below to this config block:
    #   task_reject_on_worker_lost=True,
    #
    # With that setting, if the worker process is killed or crashes without
    # calling task.ack(), the broker receives a NACK and automatically
    # re-queues the message for another worker to pick up. Combined with
    # fixing start.sh to send SIGTERM (warm shutdown) instead of letting
    # SIGINT trigger cold shutdown, no task is ever silently purged.
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    # A 20-page bidder at ~3s/page plus rate-limit backoff fits comfortably
    # inside an hour; anything longer is a stuck task, not a slow one
    task_time_limit=3600,
    task_soft_time_limit=3300,
    result_expires=86400,
)
