from dataclasses import dataclass
from typing import Any

import httpx

from relay.social.meta import MetaSettings, get_meta_settings
from relay.social.models import Channel, ChannelConnection


class MetaPublishPermanentError(Exception):
    """Meta rejected content or Relay configuration cannot publish it."""


class MetaPublishTransientError(Exception):
    """A later retry may succeed without changing content or credentials."""


@dataclass(frozen=True)
class MetaPublishedContent:
    provider_publication_id: str


class MetaPublishingClient:
    def __init__(self, config: MetaSettings | None = None) -> None:
        self.config = config or get_meta_settings()

    def publish_image(
        self, *, connection: ChannelConnection, access_token: str, body: str, image_url: str
    ) -> MetaPublishedContent:
        with httpx.Client(timeout=20.0) as client:
            if connection.channel == Channel.META_FACEBOOK_PAGE:
                response = self._post(
                    client,
                    f"/{connection.provider_channel_id}/photos",
                    {"url": image_url, "caption": body, "access_token": access_token},
                )
                return MetaPublishedContent(provider_publication_id=self._id(response))
            if connection.channel == Channel.META_INSTAGRAM_BUSINESS_ACCOUNT:
                container = self._post(
                    client,
                    f"/{connection.provider_channel_id}/media",
                    {"image_url": image_url, "caption": body, "access_token": access_token},
                )
                published = self._post(
                    client,
                    f"/{connection.provider_channel_id}/media_publish",
                    {"creation_id": self._id(container), "access_token": access_token},
                )
                return MetaPublishedContent(provider_publication_id=self._id(published))
        raise MetaPublishPermanentError("Unsupported Meta channel.")

    def _post(self, client: httpx.Client, path: str, data: dict[str, str]) -> dict[str, Any]:
        try:
            response = client.post(f"{self.config.graph_url}{path}", data=data)
        except httpx.RequestError as error:
            raise MetaPublishTransientError("Meta could not be reached.") from error
        if response.status_code == 429 or response.status_code >= 500:
            raise MetaPublishTransientError("Meta temporarily rejected the request.")
        if response.is_error:
            raise MetaPublishPermanentError("Meta rejected the publication request.")
        try:
            return response.json()
        except ValueError as error:
            raise MetaPublishPermanentError("Meta returned an invalid publication response.") from error

    @staticmethod
    def _id(payload: dict[str, Any]) -> str:
        value = payload.get("id")
        if not value:
            raise MetaPublishPermanentError("Meta did not return a publication identifier.")
        return str(value)
