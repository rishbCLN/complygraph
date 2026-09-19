"""Evidence freshness computation and file hashing."""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

from app.core.enums import EvidenceStatus

# Evidence with no explicit expiry is considered stale after this many days.
DEFAULT_STALE_DAYS = 180


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def compute_freshness(
    collected_at: datetime | None,
    expires_at: datetime | None,
    now: datetime | None = None,
) -> str:
    now = now or datetime.now(timezone.utc)
    if expires_at is not None:
        if _aware(expires_at) < now:
            return EvidenceStatus.EXPIRED.value
        # Within 14 days of expiry -> stale warning.
        if _aware(expires_at) - now < timedelta(days=14):
            return EvidenceStatus.STALE.value
        return EvidenceStatus.FRESH.value
    if collected_at is not None:
        age = now - _aware(collected_at)
        if age > timedelta(days=DEFAULT_STALE_DAYS):
            return EvidenceStatus.STALE.value
        return EvidenceStatus.FRESH.value
    return EvidenceStatus.UNKNOWN.value


def hash_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
