"""Block startup until PostgreSQL and Redis are reachable.

Used by the API and worker entrypoints so services do not declare themselves
healthy/ready before their dependencies are available.
"""

from __future__ import annotations

import sys
import time

import redis
from sqlalchemy import create_engine, text

from app.core.config import settings


def wait_for_postgres(timeout: int = 60) -> bool:
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("[wait] postgres is reachable")
            return True
        except Exception as exc:  # noqa: BLE001
            print(f"[wait] postgres not ready: {exc}")
            time.sleep(2)
    return False


def wait_for_redis(timeout: int = 60) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            client = redis.Redis.from_url(settings.redis_url)
            client.ping()
            print("[wait] redis is reachable")
            return True
        except Exception as exc:  # noqa: BLE001
            print(f"[wait] redis not ready: {exc}")
            time.sleep(2)
    return False


def main() -> None:
    # Local SQLite mode has no external dependencies to wait for.
    if settings.database_url.startswith("sqlite"):
        print("[wait] sqlite mode — no external services to wait for")
        return
    ok_pg = wait_for_postgres()
    ok_redis = wait_for_redis()
    if not (ok_pg and ok_redis):
        print("[wait] dependencies not ready in time", file=sys.stderr)
        sys.exit(1)
    print("[wait] all dependencies ready")


if __name__ == "__main__":
    main()
