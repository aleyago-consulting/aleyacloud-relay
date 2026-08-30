from django.db import models

from relay.common.models import LifecycleState, TimeStampedUUIDModel


class Post(TimeStampedUUIDModel):
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.CASCADE, related_name="posts")
    brand = models.ForeignKey("tenancy.Brand", on_delete=models.CASCADE, related_name="posts")
    title = models.CharField(max_length=255, blank=True)
    body = models.TextField(blank=True)
    state = models.CharField(max_length=32, choices=LifecycleState.choices, default=LifecycleState.DRAFT)
    created_by_subject = models.CharField(max_length=255, blank=True)
    idempotency_key = models.CharField(max_length=255)
    request_fingerprint = models.CharField(max_length=64)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("tenant", "idempotency_key"), name="unique_post_idempotency_key"
            )
        ]


class MediaAsset(TimeStampedUUIDModel):
    class UploadState(models.TextChoices):
        PENDING = "PENDING", "Pending upload"
        READY = "READY", "Ready"
        FAILED = "FAILED", "Upload failed"

    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.CASCADE, related_name="media_assets")
    brand = models.ForeignKey("tenancy.Brand", on_delete=models.CASCADE, related_name="media_assets")
    storage_key = models.CharField(max_length=1024, unique=True)
    content_type = models.CharField(max_length=255)
    size_bytes = models.PositiveBigIntegerField()
    checksum = models.CharField(max_length=128, blank=True)
    upload_state = models.CharField(
        max_length=16, choices=UploadState.choices, default=UploadState.PENDING
    )


class PostVariant(TimeStampedUUIDModel):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="variants")
    body = models.TextField(blank=True)
    media_assets = models.ManyToManyField(MediaAsset, related_name="post_variants", blank=True)
    # A many-to-many relation has no author-facing order. Keep the requested order
    # separately because it is the slide order that Meta receives for a carousel.
    media_asset_order = models.JSONField(default=list, blank=True)
    channel_hint = models.CharField(max_length=64, blank=True)
