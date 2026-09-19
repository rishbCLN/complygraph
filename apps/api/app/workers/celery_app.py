"""Celery application.

When a Redis broker is reachable, scans run on the dedicated worker. When Redis
is unavailable (local no-Docker mode), tasks fall back to eager in-process
execution so the application remains fully usable.
"""

from __future__ import annotations

import logging

from celery import Celery

from app.core.config import settings

logger = logging.getLogger("complygraph.worker")


def _redis_available() -> bool:
    try:
        import redis

        redis.Redis.from_url(settings.redis_url, socket_connect_timeout=1).ping()
        return True
    except Exception:  # noqa: BLE001
        return False


REDIS_UP = _redis_available()

celery_app = Celery(
    "complygraph",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_always_eager=not REDIS_UP,
    task_eager_propagates=True,
    worker_hijack_root_logger=False,
)

# Ensure task modules are imported so they register with the app.
import app.workers.tasks  # noqa: E402,F401
