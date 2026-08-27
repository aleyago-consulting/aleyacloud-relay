from django.db import models

from relay.common.models import TimeStampedUUIDModel


class Provider(models.TextChoices):
    META = "META", "Meta"


class Channel(models.TextChoices):
    META_FACEBOOK_PAGE = "META_FACEBOOK_PAGE", "Meta Facebook Page"
    META_INSTAGRAM_BUSINESS_ACCOUNT = (
        "META_INSTAGRAM_BUSINESS_ACCOUNT",
        "Meta Instagram Business Account",
    )


class SocialAccount(TimeStampedUUIDModel):
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.CASCADE, related_name="social_accounts")
    brand = models.ForeignKey("tenancy.Brand", on_delete=models.CASCADE, related_name="social_accounts")
    provider = models.CharField(max_length=32, choices=Provider.choices)
    provider_account_id = models.CharField(max_length=255)
    display_name = models.CharField(max_length=255, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("tenant", "provider", "provider_account_id"),
                name="unique_social_account_per_tenant",
            )
        ]


class ChannelConnection(TimeStampedUUIDModel):
    social_account = models.ForeignKey(
        SocialAccount, on_delete=models.CASCADE, related_name="channel_connections"
    )
    channel = models.CharField(max_length=64, choices=Channel.choices)
    provider_channel_id = models.CharField(max_length=255)
    display_name = models.CharField(max_length=255, blank=True)
    encrypted_access_token = models.TextField()
    token_expires_at = models.DateTimeField(null=True, blank=True)
    granted_scopes = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("social_account", "channel", "provider_channel_id"),
                name="unique_channel_connection_per_account",
            )
        ]


class OAuthState(TimeStampedUUIDModel):
    tenant = models.ForeignKey("tenancy.Tenant", on_delete=models.CASCADE, related_name="oauth_states")
    brand = models.ForeignKey("tenancy.Brand", on_delete=models.CASCADE, related_name="oauth_states")
    state_digest = models.CharField(max_length=64, unique=True)
    subject = models.CharField(max_length=255)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=("expires_at",), name="oauthstate_expiry_idx")]
