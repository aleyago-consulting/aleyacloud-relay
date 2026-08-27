from django.db import models

from relay.common.models import TimeStampedUUIDModel


class ApprovalDecision(models.TextChoices):
    PENDING = "PENDING", "Pending"
    APPROVED = "APPROVED", "Approved"
    CHANGES_REQUESTED = "CHANGES_REQUESTED", "Changes requested"


class ApprovalRequest(TimeStampedUUIDModel):
    brand = models.ForeignKey("tenancy.Brand", on_delete=models.CASCADE, related_name="approval_requests")
    post = models.ForeignKey("content.Post", on_delete=models.CASCADE, related_name="approval_requests")
    requested_by_subject = models.CharField(max_length=255)
    token_digest = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decision = models.CharField(
        max_length=32, choices=ApprovalDecision.choices, default=ApprovalDecision.PENDING
    )


class ApprovalComment(TimeStampedUUIDModel):
    approval_request = models.ForeignKey(
        ApprovalRequest, on_delete=models.CASCADE, related_name="comments"
    )
    author_label = models.CharField(max_length=255, blank=True)
    body = models.TextField()
