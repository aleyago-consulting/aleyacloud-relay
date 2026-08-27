from datetime import timedelta
from urllib.parse import parse_qs, urlparse

import pytest
from cryptography.fernet import Fernet
from django.test import override_settings
from django.utils import timezone

from relay.social.crypto import decrypt_token, encrypt_token
from relay.social.meta import MetaConnection, MetaIdentity, MetaToken
from relay.social.models import OAuthState
from relay.social.services import InvalidOAuthState, consume_oauth_state, persist_meta_connections, start_meta_oauth
from relay.tenancy.models import Brand, Tenant


pytestmark = pytest.mark.django_db


@override_settings(
    META_APP_ID="meta-app-id",
    META_APP_SECRET="meta-app-secret",
    META_REDIRECT_URI="https://relay.alyacloud.com/api/v1/oauth/meta/callback/",
    META_GRAPH_VERSION="v1.0",
)
def test_meta_authorization_state_is_opaque_and_single_use() -> None:
    tenant = Tenant.objects.create(slug="oauth", name="OAuth")
    brand = Brand.objects.create(workspace=tenant, slug="oauth", name="OAuth Brand")
    authorization = start_meta_oauth(tenant=tenant, brand=brand, subject="client:test")
    query = parse_qs(urlparse(authorization.authorization_url).query)
    raw_state = query["state"][0]

    assert OAuthState.objects.filter(tenant=tenant, state_digest=raw_state).exists() is False
    state = consume_oauth_state(raw_state)

    assert state.tenant_id == tenant.id
    with pytest.raises(InvalidOAuthState):
        consume_oauth_state(raw_state)


@override_settings(TOKEN_ENCRYPTION_KEY=Fernet.generate_key().decode("utf-8"))
def test_meta_connections_store_only_encrypted_tokens() -> None:
    tenant = Tenant.objects.create(slug="meta", name="Meta")
    brand = Brand.objects.create(workspace=tenant, slug="meta", name="Meta Brand")
    token = MetaToken(access_token="provider-secret", expires_at=timezone.now() + timedelta(days=60))
    identity = MetaIdentity(
        provider_account_id="meta-user-1",
        display_name="Meta User",
        connections=[
            MetaConnection(
                channel="META_FACEBOOK_PAGE",
                provider_channel_id="page-1",
                display_name="Page One",
                access_token="provider-secret",
            )
        ],
    )

    account = persist_meta_connections(
        tenant=tenant,
        brand=brand,
        subject="client:test",
        token=token,
        identity=identity,
    )
    connection = account.channel_connections.get()

    assert connection.encrypted_access_token != "provider-secret"
    assert decrypt_token(connection.encrypted_access_token) == "provider-secret"
    assert encrypt_token("provider-secret") != "provider-secret"
