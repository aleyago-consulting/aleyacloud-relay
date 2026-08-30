from datetime import timedelta
from typing import Protocol

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from relay.audit.models import AuditLog
from relay.common.models import LifecycleState
from relay.content.delivery import MediaDeliveryUnavailable, publishable_image_url
from relay.content.services import ordered_media_assets
from relay.publications.models import Publication, PublicationAttempt
from relay.social.crypto import TokenEncryptionError, decrypt_token
from relay.social.meta import MetaConfigurationError
from relay.social.publishing import (
    MetaPublishPermanentError,
    MetaPublishTransientError,
    MetaPublishingClient,
)


class Publisher(Protocol):
    def publish_images(
        self, *, connection, access_token: str, body: str, image_urls: list[str]
    ): ...


def _retry_delay(attempt_number: int) -> timedelta:
    return timedelta(minutes=min(2**attempt_number, 30))


def publish_due_publication(*, publication_id, publisher: Publisher | None = None) -> str:
    """Claim one due publication and record one immutable delivery attempt."""
    now = timezone.now()
    with transaction.atomic():
        publication = (
            Publication.objects.select_for_update()
            .select_related("tenant", "brand", "post_variant", "channel_connection")
            .prefetch_related("post_variant__media_assets")
            .filter(id=publication_id, state=LifecycleState.SCHEDULED, scheduled_for__lte=now)
            .first()
        )
        if publication is None:
            return "not_due_or_claimed"
        attempt = PublicationAttempt.objects.create(
            publication=publication,
            attempt_number=publication.attempts.count() + 1,
            started_at=now,
        )
        publication.state = LifecycleState.PUBLISHING
        publication.save(update_fields=("state", "updated_at"))

    try:
        media = ordered_media_assets(variant=publication.post_variant)
        if not 1 <= len(media) <= 10:
            raise MetaPublishPermanentError(
                "A publication must contain between one and ten image assets."
            )
        result = (publisher or MetaPublishingClient()).publish_images(
            connection=publication.channel_connection,
            access_token=decrypt_token(publication.channel_connection.encrypted_access_token),
            body=publication.post_variant.body,
            image_urls=[publishable_image_url(asset) for asset in media],
        )
    except MetaPublishTransientError as error:
        return _finish_failure(publication, attempt, error, transient=True)
    except (MetaPublishPermanentError, MediaDeliveryUnavailable, MetaConfigurationError, TokenEncryptionError) as error:
        return _finish_failure(publication, attempt, error, transient=False)

    with transaction.atomic():
        publication = Publication.objects.select_for_update().get(id=publication.id)
        attempt = PublicationAttempt.objects.select_for_update().get(id=attempt.id)
        attempt.outcome = "PUBLISHED"
        attempt.completed_at = timezone.now()
        attempt.save(update_fields=("outcome", "completed_at", "updated_at"))
        publication.state = LifecycleState.PUBLISHED
        publication.provider_publication_id = result.provider_publication_id
        publication.last_error_code = ""
        publication.last_error_message = ""
        publication.save(update_fields=("state", "provider_publication_id", "last_error_code", "last_error_message", "updated_at"))
        AuditLog.objects.create(tenant=publication.tenant, brand=publication.brand, actor_type="worker", actor_id="celery", event_type="publication.published", subject_type="publication", subject_id=publication.id, metadata={"attempt": attempt.attempt_number})
    return "published"


def _finish_failure(publication: Publication, attempt: PublicationAttempt, error: Exception, *, transient: bool) -> str:
    with transaction.atomic():
        publication = Publication.objects.select_for_update().get(id=publication.id)
        attempt = PublicationAttempt.objects.select_for_update().get(id=attempt.id)
        attempt.outcome = "RETRY" if transient and attempt.attempt_number < settings.RELAY_PUBLICATION_MAX_ATTEMPTS else "FAILED"
        attempt.error_code = error.__class__.__name__
        attempt.error_message = str(error)
        attempt.completed_at = timezone.now()
        attempt.save(update_fields=("outcome", "error_code", "error_message", "completed_at", "updated_at"))
        should_retry = transient and attempt.attempt_number < settings.RELAY_PUBLICATION_MAX_ATTEMPTS
        publication.state = LifecycleState.SCHEDULED if should_retry else LifecycleState.FAILED
        publication.scheduled_for = timezone.now() + _retry_delay(attempt.attempt_number) if should_retry else publication.scheduled_for
        publication.last_error_code = attempt.error_code
        publication.last_error_message = attempt.error_message
        publication.save(update_fields=("state", "scheduled_for", "last_error_code", "last_error_message", "updated_at"))
        AuditLog.objects.create(tenant=publication.tenant, brand=publication.brand, actor_type="worker", actor_id="celery", event_type="publication.retry_scheduled" if should_retry else "publication.failed", subject_type="publication", subject_id=publication.id, metadata={"attempt": attempt.attempt_number, "error_code": attempt.error_code})
    return "retry_scheduled" if should_retry else "failed"
