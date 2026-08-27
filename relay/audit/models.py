from django.db import models

from relay.common.models import TimeStampedUUIDModel


class AuditLog(TimeStampedUUIDModel):
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.CASCADE, related_name="audit_logs")
    brand = models.ForeignKey(
        "tenancy.Brand",
        on_delete=models.SET_NULL,
        related_name="audit_logs",
        null=True,
        blank=True,
    )
    actor_type = models.CharField(max_length=64)
    actor_id = models.CharField(max_length=255)
    event_type = models.CharField(max_length=100)
    subject_type = models.CharField(max_length=100)
    subject_id = models.UUIDField()
    metadata = models.JSONField(default=dict)

    class Meta:
        indexes = [models.Index(fields=("tenant", "created_at"), name="auditlog_tenant_created_idx")]
