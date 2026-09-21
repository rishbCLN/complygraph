"""TOTP (RFC 6238) multi-factor primitives, implemented on the standard library.

We deliberately avoid a third-party OTP dependency: TOTP is a small, well-
specified algorithm (HMAC-based OTP over a time counter, RFC 6238/4226) and a
self-contained implementation keeps the auth path auditable and free of extra
supply-chain surface. The functions here are pure and side-effect free; secret
storage/encryption is handled by the MFA service.

Base32 secrets follow the ``otpauth://`` convention used by Google
Authenticator, Authy, 1Password, etc., so enrolment QR codes interoperate.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote, urlencode


def generate_secret(length: int = 20) -> str:
    """Return a new random base32 TOTP secret (no padding), default 160 bits."""
    raw = secrets.token_bytes(length)
    return base64.b32encode(raw).decode("ascii").rstrip("=")


def _hotp(secret_b32: str, counter: int, digits: int) -> str:
    # Re-pad the base32 secret (b32decode requires a multiple of 8 chars).
    padding = "=" * (-len(secret_b32) % 8)
    key = base64.b32decode(secret_b32.upper() + padding, casefold=True)
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    binary = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(binary % (10**digits)).zfill(digits)


def generate_totp(
    secret_b32: str,
    *,
    digits: int = 6,
    period: int = 30,
    at: float | None = None,
) -> str:
    """Return the current TOTP code for the given secret."""
    now = time.time() if at is None else at
    counter = int(now // period)
    return _hotp(secret_b32, counter, digits)


def verify_totp(
    secret_b32: str,
    code: str,
    *,
    digits: int = 6,
    period: int = 30,
    valid_window: int = 1,
    at: float | None = None,
) -> bool:
    """Constant-time verify a submitted code, tolerating +/- ``valid_window`` steps.

    The window absorbs clock skew between the server and the authenticator app.
    """
    code = (code or "").strip().replace(" ", "")
    if not code.isdigit() or len(code) != digits:
        return False
    now = time.time() if at is None else at
    counter = int(now // period)
    for drift in range(-valid_window, valid_window + 1):
        candidate = _hotp(secret_b32, counter + drift, digits)
        if hmac.compare_digest(candidate, code):
            return True
    return False


def provisioning_uri(
    secret_b32: str,
    *,
    account_name: str,
    issuer: str,
    digits: int = 6,
    period: int = 30,
) -> str:
    """Build an ``otpauth://totp/...`` URI for authenticator-app enrolment/QR."""
    label = quote(f"{issuer}:{account_name}")
    params = urlencode(
        {
            "secret": secret_b32,
            "issuer": issuer,
            "algorithm": "SHA1",
            "digits": digits,
            "period": period,
        }
    )
    return f"otpauth://totp/{label}?{params}"


def generate_backup_codes(count: int = 10) -> list[str]:
    """Return single-use recovery codes in ``xxxx-xxxx`` form (unambiguous chars)."""
    alphabet = "23456789abcdefghjkmnpqrstuvwxyz"  # no 0/o/1/l/i ambiguity
    codes: list[str] = []
    for _ in range(count):
        chunk = "".join(secrets.choice(alphabet) for _ in range(8))
        codes.append(f"{chunk[:4]}-{chunk[4:]}")
    return codes


def normalize_backup_code(code: str) -> str:
    return (code or "").strip().lower().replace(" ", "")


def hash_backup_code(code: str) -> str:
    """Hash a backup code for at-rest comparison (codes are also encrypted as a set)."""
    return hashlib.sha256(normalize_backup_code(code).encode("utf-8")).hexdigest()
