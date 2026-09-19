"""Authentication service: login, logout, session validation, password change."""

from __future__ import annotations

import time
import uuid
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import utcnow
from app.core.errors import AuthError, RateLimitError, ValidationError
from app.models.identity import Membership, Organization, Session as UserSession, User
from app.security.passwords import hash_password, verify_password
from app.security.tokens import generate_session_token, hash_token

# In-process login rate limiter (per email). Sufficient for the local monolith.
_login_attempts: dict[str, list[float]] = {}


def _check_rate_limit(email: str) -> None:
    now = time.time()
    window = settings.login_rate_limit_window_seconds
    attempts = [t for t in _login_attempts.get(email, []) if now - t < window]
    if len(attempts) >= settings.login_rate_limit_attempts:
        raise RateLimitError("Too many login attempts. Please wait and try again.")
    attempts.append(now)
    _login_attempts[email] = attempts


def _reset_rate_limit(email: str) -> None:
    _login_attempts.pop(email, None)


def authenticate(db: Session, email: str, password: str) -> User:
    email = email.strip().lower()
    _check_rate_limit(email)
    user = db.scalar(select(User).where(User.email == email))
    if not user or not user.is_active or not verify_password(password, user.password_hash):
        raise AuthError("Invalid email or password.")
    _reset_rate_limit(email)
    return user


def create_session(db: Session, user: User) -> str:
    token = generate_session_token()
    session = UserSession(
        user_id=user.id,
        token_hash=hash_token(token),
        expires_at=utcnow() + timedelta(hours=settings.session_ttl_hours),
        created_at=utcnow(),
    )
    db.add(session)
    db.flush()
    return token


def resolve_session(db: Session, token: str) -> User:
    session = db.scalar(select(UserSession).where(UserSession.token_hash == hash_token(token)))
    if not session or session.revoked_at is not None:
        raise AuthError("Session is invalid or has been revoked.")
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        from datetime import timezone

        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < utcnow():
        raise AuthError("Session has expired.")
    user = db.get(User, session.user_id)
    if not user or not user.is_active:
        raise AuthError("User account is inactive.")
    return user


def revoke_session(db: Session, token: str) -> None:
    session = db.scalar(select(UserSession).where(UserSession.token_hash == hash_token(token)))
    if session and session.revoked_at is None:
        session.revoked_at = utcnow()


def change_password(db: Session, user: User, current_password: str, new_password: str) -> None:
    if not verify_password(current_password, user.password_hash):
        raise AuthError("Current password is incorrect.")
    if len(new_password) < 10:
        raise ValidationError("New password must be at least 10 characters.")
    user.password_hash = hash_password(new_password)
    # Revoke all other sessions for safety.
    for session in db.scalars(select(UserSession).where(UserSession.user_id == user.id)):
        if session.revoked_at is None:
            session.revoked_at = utcnow()


def primary_membership(db: Session, user: User) -> Membership:
    membership = db.scalar(select(Membership).where(Membership.user_id == user.id))
    if not membership:
        raise AuthError("User is not a member of any organization.")
    return membership


def get_membership(db: Session, user: User, organization_id: uuid.UUID) -> Membership | None:
    return db.scalar(
        select(Membership).where(
            Membership.user_id == user.id,
            Membership.organization_id == organization_id,
        )
    )


def get_organization(db: Session, organization_id: uuid.UUID) -> Organization | None:
    return db.get(Organization, organization_id)
