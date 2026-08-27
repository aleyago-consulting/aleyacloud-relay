from dataclasses import dataclass
from uuid import UUID

import jwt
from django.conf import settings
from rest_framework import authentication, exceptions


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
