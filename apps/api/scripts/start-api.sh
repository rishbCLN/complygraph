#!/usr/bin/env bash
set -euo pipefail

echo "[start-api] waiting for database..."
python -m app.core.wait_for_services

echo "[start-api] running migrations..."
alembic upgrade head

if [ "${DEMO_MODE:-true}" = "true" ]; then
  echo "[start-api] seeding demo data (idempotent)..."
  python -m app.seed || echo "[start-api] seed step reported an issue (continuing)"
fi

echo "[start-api] starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers
