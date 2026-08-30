from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

from relay.social.models import Channel
from relay.social.publishing import MetaPublishedContent, MetaPublishingClient


def _connection(channel):
    return SimpleNamespace(channel=channel, provider_channel_id="channel-1")


def _client() -> MetaPublishingClient:
    return MetaPublishingClient(config=SimpleNamespace(graph_url="https://graph.example.test"))


def test_facebook_carousel_uploads_unpublished_images_then_creates_one_feed_post() -> None:
    publisher = _client()
    http_client = MagicMock()
    with (
        patch("relay.social.publishing.httpx.Client") as client_class,
        patch.object(
            publisher,
            "_post",
            side_effect=[{"id": "photo-1"}, {"id": "photo-2"}, {"id": "feed-1"}],
        ) as post,
    ):
        client_class.return_value.__enter__.return_value = http_client
        result = publisher.publish_images(
            connection=_connection(Channel.META_FACEBOOK_PAGE),
            access_token="page-token",
            body="A carousel",
            image_urls=["https://media.test/one.jpg", "https://media.test/two.jpg"],
        )

    assert result == MetaPublishedContent(provider_publication_id="feed-1")
    assert post.call_args_list == [
        call(
            http_client,
            "/channel-1/photos",
            {"url": "https://media.test/one.jpg", "published": "false", "access_token": "page-token"},
        ),
        call(
            http_client,
            "/channel-1/photos",
            {"url": "https://media.test/two.jpg", "published": "false", "access_token": "page-token"},
        ),
        call(
            http_client,
            "/channel-1/feed",
            {
                "message": "A carousel",
                "attached_media": '[{"media_fbid": "photo-1"}, {"media_fbid": "photo-2"}]',
                "access_token": "page-token",
            },
        ),
    ]


def test_instagram_carousel_waits_for_child_and_parent_containers_before_publishing() -> None:
    publisher = _client()
    http_client = MagicMock()
    with (
        patch("relay.social.publishing.httpx.Client") as client_class,
        patch.object(
            publisher,
            "_post",
            side_effect=[{"id": "child-1"}, {"id": "child-2"}, {"id": "parent"}, {"id": "post-1"}],
        ) as post,
        patch.object(publisher, "_wait_for_instagram_container") as wait,
    ):
        client_class.return_value.__enter__.return_value = http_client
        result = publisher.publish_images(
            connection=_connection(Channel.META_INSTAGRAM_BUSINESS_ACCOUNT),
            access_token="instagram-token",
            body="A carousel",
            image_urls=["https://media.test/one.jpg", "https://media.test/two.jpg"],
        )

    assert result == MetaPublishedContent(provider_publication_id="post-1")
    assert wait.call_args_list == [
        call(http_client, "child-1", "instagram-token"),
        call(http_client, "child-2", "instagram-token"),
        call(http_client, "parent", "instagram-token"),
    ]
    assert post.call_args_list[-2:] == [
        call(
            http_client,
            "/channel-1/media",
            {
                "media_type": "CAROUSEL",
                "children": "child-1,child-2",
                "caption": "A carousel",
                "access_token": "instagram-token",
            },
        ),
        call(
            http_client,
            "/channel-1/media_publish",
            {"creation_id": "parent", "access_token": "instagram-token"},
        ),
    ]
