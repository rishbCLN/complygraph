"""Multi-factor authentication (TOTP) service (feature #10).

Enrolment is a two-step ceremony so a user cannot lock themselves out with a
mistyped code:

1. ``begin_enrollment`` generates and stores an (encrypted) pending secret and
   returns the ``otpauth://`` provisioning URI. MFA is NOT yet active.
2. ``activate`` verifies a code from the authenticator against the pending
   secret, flips ``mfa_enabled`` on, and returns one-time backup codes.

At login, ``issue_challenge``/``decode_challenge`` carry a short-lived signed
token between the password step and the second-factor step, and
``verify_second_factor`` accepts either a live TOTP code or a single-use backup
code (which is then consumed).

Secrets and backup-code hashes are Fernet-encrypted at rest; plaintext codes
are shown to the user exactly once.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import jwt

from app.core.config import settings
from app.core.database import utcnow
from app.core.errors import AuthError, ValidationError
from app.models.identity import User
from app.security.encryption import decrypt_json, encrypt_json
from app.security.passwords import verify_password
from app.security.totp import (
    generate_backup_codes,
    generate_secret,
    generate_totp,
    hash_backup_code,
    provisioning_uri,
    verify_totp,
)

_CHALLENGE_PURPOSE = "mfa_challenge"


@dataclass
class EnrollmentStart:
    secret: str
    otpauth_uri: str


def _store_secret(user: User, secret: str) -> None:
    user.mfa_secret_encrypted = encrypt_json({"secret": secret})


def _load_secret(user: User) -> str | None:
    if not user.mfa_secret_encrypted:
        return None
    try:
        return decrypt_json(user.mfa_secret_encrypted).get("secret")
    except ValueError:
        return None


def _store_backup_codes(user: User, codes: list[str]) -> None:
    hashes = [hash_backup_code(c) for c in codes]
    user.mfa_backup_codes_encrypted = encrypt_json({"codes": hashes})


def _load_backup_hashes(user: User) -> list[str]:
    if not user.mfa_backup_codes_encrypted:
        return []
    try:
        return list(decrypt_json(user.mfa_backup_codes_encrypted).get("codes", []))
    except ValueError:
        return []


def begin_enrollment(user: User) -> EnrollmentStart:
    """Generate a pending TOTP secret and provisioning URI (not yet active)."""
    if not settings.mfa_enabled:
        raise ValidationError("MFA is not enabled for this deployment.")
    if user.mfa_enabled:
        raise ValidationError("MFA is already enabled. Disable it first to re-enrol.")
    secret = generate_secret()
    _store_secret(user, secret)
    uri = provisioning_uri(
        secret,
        account_name=user.email,
        issuer=settings.mfa_issuer_name,
        digits=settings.mfa_totp_digits,
        period=settings.mfa_totp_period_seconds,
    )
    return EnrollmentStart(secret=secret, otpauth_uri=uri)


def activate(user: User, code: str) -> list[str]:
    """Verify the first code and enable MFA; returns one-time backup codes."""
    if not settings.mfa_enabled:
        raise ValidationError("MFA is not enabled for this deployment.")
    secret = _load_secret(user)
    if not secret:
        raise ValidationError("Start enrolment before activating MFA.")
    if not _verify_code(secret, code):
        raise ValidationError("That code is incorrect. Check your authenticator and try again.")
    codes = generate_backup_codes(settings.mfa_backup_code_count)
    _store_backup_codes(user, codes)
    user.mfa_enabled = True
    user.mfa_enrolled_at = utcnow()
    return codes


def disable(user: User, password: str) -> None:
    """Turn MFA off after re-verifying the account password."""
    if not verify_password(password, user.password_hash):
        raise AuthError("Password is incorrect.")
    user.mfa_enabled = False
    user.mfa_secret_encrypted = None
    user.mfa_backup_codes_encrypted = None
    user.mfa_enrolled_at = None


def regenerate_backup_codes(user: User) -> list[str]:
    if not user.mfa_enabled:
        raise ValidationError("Enable MFA before generating backup codes.")
    codes = generate_backup_codes(settings.mfa_backup_code_count)
    _store_backup_codes(user, codes)
    return codes


def _verify_code(secret: str, code: str) -> bool:
    return verify_totp(
        secret,
        code,
        digits=settings.mfa_totp_digits,
        period=settings.mfa_totp_period_seconds,
        valid_window=settings.mfa_totp_valid_window,
    )


def verify_second_factor(user: User, code: str) -> bool:
    """Accept a live TOTP code or consume a single-use backup code."""
    secret = _load_secret(user)
    if secret and _verify_code(secret, code):
        return True
    # Fall back to backup codes (consume on use).
    target = hash_backup_code(code)
    hashes = _load_backup_hashes(user)
    if target in hashes:
        hashes.remove(target)
        user.mfa_backup_codes_encrypted = encrypt_json({"codes": hashes})
        return True
    return False


def current_code(user: User) -> str | None:
    """Return the current TOTP code (used only by tests / never exposed via API)."""
    secret = _load_secret(user)
    if not secret:
        return None
    return generate_totp(
        secret, digits=settings.mfa_totp_digits, period=settings.mfa_totp_period_seconds
    )


def issue_challenge(user: User) -> str:
    """Mint a short-lived signed token binding a pending login to a second factor."""
    now = utcnow()
    payload = {
        "sub": str(user.id),
        "purpose": _CHALLENGE_PURPOSE,
        "iat": int(now.timestamp()),
        "exp": int(now.timestamp()) + settings.mfa_challenge_ttl_seconds,
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_challenge(token: str) -> uuid.UUID:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise AuthError("Your login session expired. Please sign in again.") from None
    except jwt.PyJWTError:
        raise AuthError("Invalid MFA challenge.") from None
    if payload.get("purpose") != _CHALLENGE_PURPOSE:
        raise AuthError("Invalid MFA challenge.")
    try:
        return uuid.UUID(payload["sub"])
    except (KeyError, ValueError):
        raise AuthError("Invalid MFA challenge.") from None
