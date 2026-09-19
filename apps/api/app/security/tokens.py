"""Session token utilities.

Sessions are stored server-side (sessions table). The client only receives an
opaque random token in an HTTP-only cookie. We store only the SHA-256 hash of
the token so a database leak does not expose usable session tokens.
"""

from __future__ import annotations

import hashlib
import secrets

SESSION_COOKIE_NAME = "cg_session"


def generate_session_token() -> str:
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
