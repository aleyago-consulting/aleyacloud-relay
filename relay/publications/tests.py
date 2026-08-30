from datetime import timedelta

import pytest
from cryptography.fernet import Fernet
from django.test import override_settings
from django.utils import timezone

from relay.common.models import LifecycleState
from relay.content.models import MediaAsset, Post, PostVariant
from relay.publications.models import Publication
from relay.publications.services import publish_due_publication
from relay.social.crypto import encrypt_token
from relay.social.publishing import MetaPublishPermanentError, MetaPublishTransientError, MetaPublishedContent
from relay.social.models import Channel, ChannelConnection, Provider, SocialAccount
from relay.tenancy.models import Brand, Tenant


pytestmark = pytest.mark.django_db


class SuccessfulPublisher:
    def publish_images(self, **_: object) -> MetaPublishedContent:
        return MetaPublishedContent(provider_publication_id="meta-publication-1")


class TransientPublisher:
    def publish_images(self, **_: object) -> MetaPublishedContent:
        raise MetaPublishTransientError("Temporary Meta outage")


class RejectedPublisher:
    def publish_images(self, **_: object) -> MetaPublishedContent:
        raise MetaPublishPermanentError("Rejected by Meta")


class CapturingPublisher:
    image_urls: list[str]

    def publish_images(self, *, image_urls: list[str], **_: object) -> MetaPublishedContent:
        self.image_urls = image_urls
        return MetaPublishedContent(provider_publication_id="meta-carousel-1")


def due_publication() -> Publication:
    tenant = Tenant.objects.create(slug="delivery", name="Delivery")
    brand = Brand.objects.create(workspace=tenant, slug="delivery", name="Delivery brand")
    post = Post.objects.create(tenant=tenant, brand=brand, body="Publish this", state=LifecycleState.APPROVED, idempotency_key="delivery-post", request_fingerprint="0" * 64)
    variant = PostVariant.objects.create(post=post, body=post.body)
    asset = MediaAsset.objects.create(tenant=tenant, brand=brand, storage_key="delivery/image.jpg", content_type="image/jpeg", size_bytes=42)
    variant.media_assets.add(asset)
    account = SocialAccount.objects.create(tenant=tenant, brand=brand, provider=Provider.META, provider_account_id="account")
    connection = ChannelConnection.objects.create(social_account=account, channel=Channel.META_FACEBOOK_PAGE, provider_channel_id="page", encrypted_access_token=encrypt_token("page-token"))
    return Publication.objects.create(tenant=tenant, brand=brand, post_variant=variant, channel_connection=connection, scheduled_for=timezone.now() - timedelta(minutes=1), state=LifecycleState.SCHEDULED, idempotency_key="delivery-publication", request_fingerprint="1" * 64)


@override_settings(TOKEN_ENCRYPTION_KEY=Fernet.generate_key().decode(), RELAY_MEDIA_PUBLIC_BASE_URL="https://media.example.test/relay")
def test_due_publication_is_claimed_published_and_audited() -> None:
    publication = due_publication()
    result = publish_due_publication(publication_id=publication.id, publisher=SuccessfulPublisher())
    publication.refresh_from_db()
    assert result == "published"
    assert publication.state == LifecycleState.PUBLISHED
    assert publication.provider_publication_id == "meta-publication-1"
    assert publication.attempts.get().outcome == "PUBLISHED"


@override_settings(TOKEN_ENCRYPTION_KEY=Fernet.generate_key().decode(), RELAY_MEDIA_PUBLIC_BASE_URL="https://media.example.test/relay")
def test_transient_meta_error_reschedules_with_a_recorded_attempt() -> None:
    publication = due_publication()
    result = publish_due_publication(publication_id=publication.id, publisher=TransientPublisher())
    publication.refresh_from_db()
    assert result == "retry_scheduled"
    assert publication.state == LifecycleState.SCHEDULED
    assert publication.scheduled_for > timezone.now()
    assert publication.attempts.get().outcome == "RETRY"


@override_settings(TOKEN_ENCRYPTION_KEY=Fernet.generate_key().decode(), RELAY_MEDIA_PUBLIC_BASE_URL="https://media.example.test/relay")
def test_permanent_meta_error_fails_without_retry() -> None:
    publication = due_publication()
    result = publish_due_publication(publication_id=publication.id, publisher=RejectedPublisher())
    publication.refresh_from_db()
    assert result == "failed"
    assert publication.state == LifecycleState.FAILED
    assert publication.attempts.get().outcome == "FAILED"


@override_settings(TOKEN_ENCRYPTION_KEY=Fernet.generate_key().decode(), RELAY_MEDIA_PUBLIC_BASE_URL="https://media.example.test/relay")
def test_due_publication_sends_all_carousel_images_to_publisher() -> None:
    publication = due_publication()
    first_asset = publication.post_variant.media_assets.get()
    second_asset = MediaAsset.objects.create(
        tenant=publication.tenant,
        brand=publication.brand,
        storage_key="delivery/image-2.jpg",
        content_type="image/jpeg",
        size_bytes=43,
    )
    publication.post_variant.media_assets.add(second_asset)
    publisher = CapturingPublisher()

    result = publish_due_publication(publication_id=publication.id, publisher=publisher)

    assert result == "published"
    assert publisher.image_urls == [
        "https://media.example.test/relay/delivery/image.jpg",
        "https://media.example.test/relay/delivery/image-2.jpg",
    ]
    assert first_asset.upload_state == MediaAsset.UploadState.READY
