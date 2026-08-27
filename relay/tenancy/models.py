from django.db import models

from relay.common.models import TimeStampedUUIDModel


class Tenant(TimeStampedUUIDModel):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class MembershipRole(models.TextChoices):
    OWNER = "OWNER", "Workspace owner"
    MANAGER = "MANAGER", "Agency manager"
    CONTENT_CREATOR = "CONTENT_CREATOR", "Content creator"
    CLIENT_APPROVER = "CLIENT_APPROVER", "Client approver"
    VIEWER = "VIEWER", "Viewer"


class Brand(TimeStampedUUIDModel):
    workspace = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="brands")
    slug = models.SlugField()
    name = models.CharField(max_length=200)
    timezone = models.CharField(max_length=64, default="UTC")
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("workspace", "slug"), name="unique_brand_slug_per_workspace")
        ]
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class Membership(TimeStampedUUIDModel):
    workspace = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="memberships")
    subject = models.CharField(max_length=255)
    role = models.CharField(max_length=32, choices=MembershipRole.choices)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("workspace", "subject"), name="unique_workspace_membership")
        ]
