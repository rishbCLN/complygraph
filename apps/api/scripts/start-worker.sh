#!/usr/bin/env bash
set -euo pipefail

echo "[start-worker] waiting for services..."
python -m app.core.wait_for_services

echo "[start-worker] starting celery worker..."
exec celery -A app.workers.celery_app.celery_app worker --loglevel=info --concurrency=2
