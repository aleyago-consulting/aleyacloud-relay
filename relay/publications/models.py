from django.db import models

from relay.common.models import LifecycleState, TimeStampedUUIDModel


class Publication(TimeStampedUUIDModel):
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.CASCADE, related_name="publications")
    brand = models.ForeignKey("tenancy.Brand", on_delete=models.CASCADE, related_name="publications")
    post_variant = models.ForeignKey(
        "content.PostVariant", on_delete=models.PROTECT, related_name="publications"
    )
    channel_connection = models.ForeignKey(
        "social.ChannelConnection", on_delete=models.PROTECT, related_name="publications"
    )
    scheduled_for = models.DateTimeField()
    state = models.CharField(max_length=32, choices=LifecycleState.choices, default=LifecycleState.DRAFT)
    idempotency_key = models.CharField(max_length=255)
    request_fingerprint = models.CharField(max_length=64)
    provider_publication_id = models.CharField(max_length=255, blank=True)
    last_error_code = models.CharField(max_length=100, blank=True)
    last_error_message = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("tenant", "idempotency_key"), name="unique_publication_idempotency_key"
            )
        ]
        indexes = [
            models.Index(
                fields=("state", "scheduled_for"), name="publication_state_sched_idx"
            )
        ]


class PublicationAttempt(TimeStampedUUIDModel):
    publication = models.ForeignKey(Publication, on_delete=models.CASCADE, related_name="attempts")
    attempt_number = models.PositiveIntegerField()
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    outcome = models.CharField(max_length=32, blank=True)
    provider_status_code = models.PositiveSmallIntegerField(null=True, blank=True)
    error_code = models.CharField(max_length=100, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("publication", "attempt_number"), name="unique_publication_attempt_number"
            )
        ]
