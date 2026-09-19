"""FastAPI dependencies: auth context, org scoping, and RBAC enforcement."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import AuthError, ForbiddenError
from app.core.rbac import has_capability
from app.models.identity import Membership, Organization, User
from app.security.tokens import SESSION_COOKIE_NAME
from app.services import auth_service


@dataclass
class AuthContext:
    user: User
    membership: Membership
    organization: Organization

    @property
    def organization_id(self) -> uuid.UUID:
        return self.organization.id

    @property
    def role(self) -> str:
        return self.membership.role


def get_current_context(
    request: Request,
    db: Session = Depends(get_db),
) -> AuthContext:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        raise AuthError("Authentication required.")
    user = auth_service.resolve_session(db, token)

    # Organization selection: header override (must be a real membership) or primary.
    org_header = request.headers.get("x-organization-id")
    membership: Membership | None = None
    if org_header:
        try:
            org_id = uuid.UUID(org_header)
        except ValueError:
            raise ForbiddenError("Invalid organization identifier.") from None
        membership = auth_service.get_membership(db, user, org_id)
        if membership is None:
            raise ForbiddenError("You do not have access to this organization.")
    else:
        membership = auth_service.primary_membership(db, user)

    organization = auth_service.get_organization(db, membership.organization_id)
    if organization is None:
        raise AuthError("Organization not found.")

    request.state.user_id = str(user.id)
    request.state.organization_id = str(organization.id)
    return AuthContext(user=user, membership=membership, organization=organization)


def require_capability(capability: str):
    """Dependency factory enforcing that the caller's role has a capability."""

    def _checker(ctx: AuthContext = Depends(get_current_context)) -> AuthContext:
        if not has_capability(ctx.role, capability):
            raise ForbiddenError(
                f"Role {ctx.role} is not permitted to perform this action."
            )
        return ctx

    return _checker
