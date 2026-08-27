from dataclasses import dataclass
from datetime import timedelta
from typing import Any
from urllib.parse import urlencode

import httpx
from django.conf import settings
from django.utils import timezone


class MetaConfigurationError(Exception):
    """Required Meta OAuth configuration is absent."""


class MetaProviderError(Exception):
    """Meta rejected or could not complete a provider request."""


@dataclass(frozen=True)
class MetaSettings:
    app_id: str
    app_secret: str
    redirect_uri: str
    graph_version: str

    @property
    def graph_url(self) -> str:
        return f"https://graph.facebook.com/{self.graph_version}"


@dataclass(frozen=True)
class MetaToken:
    access_token: str
    expires_at: object | None


@dataclass(frozen=True)
class MetaConnection:
    channel: str
    provider_channel_id: str
    display_name: str
    access_token: str


@dataclass(frozen=True)
class MetaIdentity:
    provider_account_id: str
    display_name: str
    connections: list[MetaConnection]


def get_meta_settings() -> MetaSettings:
    names = ("META_APP_ID", "META_APP_SECRET", "META_REDIRECT_URI", "META_GRAPH_VERSION")
    values = {name: getattr(settings, name, "") for name in names}
    if any(not value for value in values.values()):
        raise MetaConfigurationError("Meta OAuth is not configured.")
    return MetaSettings(
        app_id=values["META_APP_ID"],
        app_secret=values["META_APP_SECRET"],
        redirect_uri=values["META_REDIRECT_URI"],
        graph_version=values["META_GRAPH_VERSION"],
    )


class MetaOAuthClient:
    scopes = (
        "public_profile",
        "pages_show_list",
        "pages_read_engagement",
        "pages_manage_posts",
        "instagram_basic",
        "instagram_content_publish",
    )

    def __init__(self, config: MetaSettings | None = None) -> None:
        self.config = config or get_meta_settings()

    def authorization_url(self, state: str) -> str:
        query = urlencode(
            {
                "client_id": self.config.app_id,
                "redirect_uri": self.config.redirect_uri,
                "state": state,
                "response_type": "code",
                "scope": ",".join(self.scopes),
            }
        )
        return f"https://www.facebook.com/{self.config.graph_version}/dialog/oauth?{query}"

    def connect(self, code: str) -> tuple[MetaToken, MetaIdentity]:
        with httpx.Client(timeout=10.0) as client:
            short_lived = self._request_token(
                client,
                {
                    "client_id": self.config.app_id,
                    "client_secret": self.config.app_secret,
                    "redirect_uri": self.config.redirect_uri,
                    "code": code,
                },
            )
            long_lived = self._request_token(
                client,
                {
                    "grant_type": "fb_exchange_token",
                    "client_id": self.config.app_id,
                    "client_secret": self.config.app_secret,
                    "fb_exchange_token": short_lived["access_token"],
                },
            )
            access_token = long_lived["access_token"]
            identity = self._discover_identity(client, access_token)

        expires_in = long_lived.get("expires_in")
        expires_at = (
            timezone.now() + timedelta(seconds=int(expires_in)) if expires_in is not None else None
        )
        return MetaToken(access_token=access_token, expires_at=expires_at), identity

    def _request_token(self, client: httpx.Client, params: dict[str, str]) -> dict[str, Any]:
        return self._request(client, "/oauth/access_token", params=params)

    def _discover_identity(self, client: httpx.Client, access_token: str) -> MetaIdentity:
        profile = self._request(client, "/me", params={"fields": "id,name", "access_token": access_token})
        pages = self._request(
            client,
            "/me/accounts",
            params={
                "fields": "id,name,access_token,instagram_business_account{id,username}",
                "access_token": access_token,
            },
        )
        connections: list[MetaConnection] = []
        for page in pages.get("data", []):
            page_token = page.get("access_token")
            if not page_token:
                continue
            connections.append(
                MetaConnection(
                    channel="META_FACEBOOK_PAGE",
                    provider_channel_id=page["id"],
                    display_name=page.get("name", ""),
                    access_token=page_token,
                )
            )
            instagram = page.get("instagram_business_account")
            if instagram:
                connections.append(
                    MetaConnection(
                        channel="META_INSTAGRAM_BUSINESS_ACCOUNT",
                        provider_channel_id=instagram["id"],
                        display_name=instagram.get("username", page.get("name", "")),
                        access_token=page_token,
                    )
                )
        return MetaIdentity(
            provider_account_id=profile["id"],
            display_name=profile.get("name", ""),
            connections=connections,
        )

    def _request(
        self, client: httpx.Client, path: str, *, params: dict[str, str]
    ) -> dict[str, Any]:
        try:
            response = client.get(f"{self.config.graph_url}{path}", params=params)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError, KeyError) as error:
            raise MetaProviderError("Meta could not complete the requested operation.") from error

