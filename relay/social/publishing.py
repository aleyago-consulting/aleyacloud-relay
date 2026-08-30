from dataclasses import dataclass
import json
from time import sleep
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

    def publish_images(
        self,
        *,
        connection: ChannelConnection,
        access_token: str,
        body: str,
        image_urls: list[str],
    ) -> MetaPublishedContent:
        if not 1 <= len(image_urls) <= 10:
            raise MetaPublishPermanentError("A Meta publication must contain between one and ten images.")
        with httpx.Client(timeout=20.0) as client:
            if connection.channel == Channel.META_FACEBOOK_PAGE:
                if len(image_urls) > 1:
                    return self._publish_facebook_carousel(
                        client, connection, access_token, body, image_urls
                    )
                response = self._post(
                    client,
                    f"/{connection.provider_channel_id}/photos",
                    {"url": image_urls[0], "caption": body, "access_token": access_token},
                )
                return MetaPublishedContent(provider_publication_id=self._id(response))
            if connection.channel == Channel.META_INSTAGRAM_BUSINESS_ACCOUNT:
                if len(image_urls) > 1:
                    return self._publish_instagram_carousel(
                        client, connection, access_token, body, image_urls
                    )
                container = self._post(
                    client,
                    f"/{connection.provider_channel_id}/media",
                    {"image_url": image_urls[0], "caption": body, "access_token": access_token},
                )
                creation_id = self._id(container)
                self._wait_for_instagram_container(client, creation_id, access_token)
                published = self._post(
                    client,
                    f"/{connection.provider_channel_id}/media_publish",
                    {"creation_id": creation_id, "access_token": access_token},
                )
                return MetaPublishedContent(provider_publication_id=self._id(published))
        raise MetaPublishPermanentError("Unsupported Meta channel.")

    def _publish_facebook_carousel(
        self,
        client: httpx.Client,
        connection: ChannelConnection,
        access_token: str,
        body: str,
        image_urls: list[str],
    ) -> MetaPublishedContent:
        media_ids = []
        for image_url in image_urls:
            uploaded = self._post(
                client,
                f"/{connection.provider_channel_id}/photos",
                {"url": image_url, "published": "false", "access_token": access_token},
            )
            media_ids.append(self._id(uploaded))
        published = self._post(
            client,
            f"/{connection.provider_channel_id}/feed",
            {
                "message": body,
                "attached_media": json.dumps([{"media_fbid": media_id} for media_id in media_ids]),
                "access_token": access_token,
            },
        )
        return MetaPublishedContent(provider_publication_id=self._id(published))

    def _publish_instagram_carousel(
        self,
        client: httpx.Client,
        connection: ChannelConnection,
        access_token: str,
        body: str,
        image_urls: list[str],
    ) -> MetaPublishedContent:
        child_ids = []
        for image_url in image_urls:
            child = self._post(
                client,
                f"/{connection.provider_channel_id}/media",
                {
                    "image_url": image_url,
                    "is_carousel_item": "true",
                    "access_token": access_token,
                },
            )
            child_id = self._id(child)
            self._wait_for_instagram_container(client, child_id, access_token)
            child_ids.append(child_id)
        container = self._post(
            client,
            f"/{connection.provider_channel_id}/media",
            {
                "media_type": "CAROUSEL",
                "children": ",".join(child_ids),
                "caption": body,
                "access_token": access_token,
            },
        )
        creation_id = self._id(container)
        self._wait_for_instagram_container(client, creation_id, access_token)
        published = self._post(
            client,
            f"/{connection.provider_channel_id}/media_publish",
            {"creation_id": creation_id, "access_token": access_token},
        )
        return MetaPublishedContent(provider_publication_id=self._id(published))

    def _post(self, client: httpx.Client, path: str, data: dict[str, Any]) -> dict[str, Any]:
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

    def _wait_for_instagram_container(
        self, client: httpx.Client, creation_id: str, access_token: str
    ) -> None:
        """Instagram creation is asynchronous; never publish an unfinished container."""
        for attempt in range(5):
            try:
                response = client.get(
                    f"{self.config.graph_url}/{creation_id}",
                    params={"fields": "status_code", "access_token": access_token},
                )
            except httpx.RequestError as error:
                raise MetaPublishTransientError("Meta could not check the Instagram media.") from error
            if response.status_code == 429 or response.status_code >= 500:
                raise MetaPublishTransientError("Meta temporarily rejected the Instagram media check.")
            if response.is_error:
                raise MetaPublishPermanentError("Meta rejected the Instagram media container.")
            try:
                status = str(response.json().get("status_code", ""))
            except ValueError as error:
                raise MetaPublishPermanentError("Meta returned an invalid Instagram media status.") from error
            if status == "FINISHED":
                return
            if status in {"ERROR", "EXPIRED"}:
                raise MetaPublishPermanentError("Meta could not process the Instagram image.")
            if attempt < 4:
                sleep(2)
        raise MetaPublishTransientError("Instagram media is still processing; Relay will retry.")

    @staticmethod
    def _id(payload: dict[str, Any]) -> str:
        value = payload.get("id")
        if not value:
            raise MetaPublishPermanentError("Meta did not return a publication identifier.")
        return str(value)
