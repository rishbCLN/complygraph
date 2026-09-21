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

# Periodic jobs (requires `celery -A app.workers.celery_app beat` alongside the worker).
_beat: dict[str, dict] = {}
if settings.scheduled_rescan_enabled and settings.scheduled_rescan_interval_hours > 0:
    _beat["scheduled-rescans"] = {
        "task": "complygraph.scheduled_rescans",
        "schedule": settings.scheduled_rescan_interval_hours * 3600.0,
    }
if settings.scheduled_reassessment_enabled and settings.scheduled_reassessment_interval_hours > 0:
    _beat["scheduled-reassessment"] = {
        "task": "complygraph.scheduled_reassessment",
        "schedule": settings.scheduled_reassessment_interval_hours * 3600.0,
    }
if settings.reminders_enabled and settings.reminders_interval_hours > 0:
    _beat["generate-reminders"] = {
        "task": "complygraph.generate_reminders",
        "schedule": settings.reminders_interval_hours * 3600.0,
    }
if _beat:
    celery_app.conf.beat_schedule = _beat

# Ensure task modules are imported so they register with the app.
import app.workers.tasks  # noqa: E402,F401
