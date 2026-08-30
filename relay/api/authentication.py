from dataclasses import dataclass
from uuid import UUID

import jwt
from django.conf import settings
from rest_framework import authentication, exceptions

from relay.tenancy.models import Brand, Membership, MembershipRole


@dataclass(frozen=True)
class RelayPrincipal:
    subject: str
    workspace_id: UUID
    brand_ids: frozenset[UUID]
    scopes: frozenset[str]

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def is_anonymous(self) -> bool:
        return False


class RelayServiceJWTAuthentication(authentication.BaseAuthentication):
    """Authenticates product-to-Relay credentials and exposes their tenant context."""

    keyword = "Bearer"

    def authenticate(self, request):
        authorization = authentication.get_authorization_header(request).split()
        if not authorization:
            return None
        if len(authorization) != 2 or authorization[0].decode().lower() != self.keyword.lower():
            raise exceptions.AuthenticationFailed("Invalid authorization header.")

        try:
            payload = jwt.decode(
                authorization[1],
                settings.RELAY_SERVICE_JWT_SECRET,
                algorithms=["HS256"],
                audience=settings.RELAY_SERVICE_JWT_AUDIENCE,
                issuer=settings.RELAY_SERVICE_JWT_ISSUER,
                options={"require": ["exp", "sub", "workspace_id", "brand_ids"]},
            )
            principal = RelayPrincipal(
                subject=str(payload["sub"]),
                workspace_id=UUID(str(payload["workspace_id"])),
                brand_ids=frozenset(UUID(str(value)) for value in payload["brand_ids"]),
                scopes=frozenset(payload.get("scopes", [])),
            )
        except (jwt.PyJWTError, KeyError, TypeError, ValueError) as error:
            raise exceptions.AuthenticationFailed("Invalid or expired service credential.") from error

        return (principal, payload)


def panel_subject(user_id: int) -> str:
    return f"user:{user_id}"


ROLE_SCOPES = {
    MembershipRole.OWNER: frozenset(
        {
            "connections:read",
            "connections:write",
            "media:write",
            "posts:read",
            "posts:write",
            "posts:approve",
            "approvals:write",
            "publications:read",
            "publications:write",
        }
    ),
    MembershipRole.MANAGER: frozenset(
        {
            "connections:read",
            "connections:write",
            "media:write",
            "posts:read",
            "posts:write",
            "posts:approve",
            "approvals:write",
            "publications:read",
            "publications:write",
        }
    ),
    MembershipRole.CONTENT_CREATOR: frozenset(
        {
            "connections:read",
            "media:write",
            "posts:read",
            "posts:write",
            "posts:approve",
            "approvals:write",
            "publications:read",
            "publications:write",
        }
    ),
    MembershipRole.CLIENT_APPROVER: frozenset({"connections:read", "posts:read", "publications:read"}),
    MembershipRole.VIEWER: frozenset({"connections:read", "posts:read", "publications:read"}),
}


def panel_principal(user, session) -> RelayPrincipal:
    """Resolve a panel user to one active workspace without trusting browser input."""
    subject = panel_subject(user.id)
    memberships = Membership.objects.filter(subject=subject, is_active=True).select_related("workspace")
    requested_workspace_id = session.get("relay_workspace_id")
    membership = memberships.filter(workspace_id=requested_workspace_id).first()
    if membership is None:
        membership = memberships.order_by("workspace__name").first()
    if membership is None or not membership.workspace.is_active:
        raise exceptions.AuthenticationFailed("This user does not have access to a Relay workspace.")

    session["relay_workspace_id"] = str(membership.workspace_id)
    brand_ids = frozenset(
        Brand.objects.filter(workspace=membership.workspace, is_active=True).values_list("id", flat=True)
    )
    return RelayPrincipal(
        subject=subject,
        workspace_id=membership.workspace_id,
        brand_ids=brand_ids,
        scopes=ROLE_SCOPES[membership.role],
    )


class RelayPanelSessionAuthentication(authentication.SessionAuthentication):
    """Authenticated browser session for the Relay React panel.

    SessionAuthentication supplies CSRF enforcement for every mutation; this
    adapter turns the Django user into the same tenant-scoped principal used by
    service-to-service API callers.
    """

    def authenticate(self, request):
        session_authentication = super().authenticate(request)
        if session_authentication is None:
            return None
        user, _ = session_authentication
        return (panel_principal(user, request.session), None)
