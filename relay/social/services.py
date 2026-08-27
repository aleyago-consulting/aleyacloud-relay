import hashlib
import secrets
from dataclasses import dataclass
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from relay.audit.models import AuditLog
from relay.social.crypto import encrypt_token
from relay.social.meta import MetaIdentity, MetaOAuthClient, MetaToken
from relay.social.models import ChannelConnection, OAuthState, Provider, SocialAccount
from relay.tenancy.models import Brand, Tenant


class InvalidOAuthState(Exception):
    """The OAuth state is invalid, expired or already used."""


@dataclass(frozen=True)
class MetaAuthorization:
    authorization_url: str


def _state_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@transaction.atomic
def start_meta_oauth(*, tenant: Tenant, brand: Brand, subject: str) -> MetaAuthorization:
    raw_state = secrets.token_urlsafe(48)
    OAuthState.objects.create(
        tenant=tenant,
        brand=brand,
        state_digest=_state_digest(raw_state),
        subject=subject,
        expires_at=timezone.now() + timedelta(minutes=10),
    )
    return MetaAuthorization(authorization_url=MetaOAuthClient().authorization_url(raw_state))


@transaction.atomic
def consume_oauth_state(raw_state: str) -> OAuthState:
    state = OAuthState.objects.select_for_update().filter(state_digest=_state_digest(raw_state)).first()
    if not state or state.used_at or state.expires_at <= timezone.now():
        raise InvalidOAuthState
    state.used_at = timezone.now()
    state.save(update_fields=("used_at", "updated_at"))
    return state


@transaction.atomic
def persist_meta_connections(
    *, tenant: Tenant, brand: Brand, subject: str, token: MetaToken, identity: MetaIdentity
) -> SocialAccount:
    account, _ = SocialAccount.objects.update_or_create(
        tenant=tenant,
        brand=brand,
        provider=Provider.META,
        provider_account_id=identity.provider_account_id,
        defaults={"display_name": identity.display_name},
    )
    for connection in identity.connections:
        ChannelConnection.objects.update_or_create(
            social_account=account,
            channel=connection.channel,
            provider_channel_id=connection.provider_channel_id,
            defaults={
                "display_name": connection.display_name,
                "encrypted_access_token": encrypt_token(connection.access_token),
                "token_expires_at": token.expires_at,
                "granted_scopes": list(MetaOAuthClient.scopes),
                "is_active": True,
            },
        )
    AuditLog.objects.create(
        tenant=tenant,
        brand=brand,
        actor_type="service",
        actor_id=subject,
        event_type="meta.connection_created",
        subject_type="social_account",
        subject_id=account.id,
        metadata={"connection_count": len(identity.connections)},
    )
    return account


def complete_meta_oauth(*, code: str, raw_state: str) -> SocialAccount:
    state = consume_oauth_state(raw_state)
    token, identity = MetaOAuthClient().connect(code)
    return persist_meta_connections(
        tenant=state.tenant,
        brand=state.brand,
        subject=state.subject,
        token=token,
        identity=identity,
    )
