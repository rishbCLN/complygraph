"""Authenticated encryption for connector credentials.

Uses Fernet (AES-128-CBC + HMAC). The key is derived from APP_ENCRYPTION_KEY.
The database only ever stores ciphertext blobs; plaintext credentials are never
persisted or logged.
"""

from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def _derive_key() -> bytes:
    """Derive a stable 32-byte urlsafe base64 Fernet key from the configured secret."""
    raw = settings.app_encryption_key.encode("utf-8")
    digest = hashlib.sha256(raw).digest()
    return base64.urlsafe_b64encode(digest)


_fernet = Fernet(_derive_key())


def encrypt_json(data: dict[str, Any]) -> str:
    payload = json.dumps(data, separators=(",", ":")).encode("utf-8")
    return _fernet.encrypt(payload).decode("utf-8")


def decrypt_json(token: str) -> dict[str, Any]:
    try:
        payload = _fernet.decrypt(token.encode("utf-8"))
    except InvalidToken as exc:  # noqa: F841
        raise ValueError("Unable to decrypt connector configuration") from None
    return json.loads(payload.decode("utf-8"))
