import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [("tenancy", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="SocialAccount",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("provider", models.CharField(choices=[("META", "Meta")], max_length=32)),
                ("provider_account_id", models.CharField(max_length=255)),
                ("display_name", models.CharField(blank=True, max_length=255)),
                (
                    "tenant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="social_accounts",
                        to="tenancy.tenant",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ChannelConnection",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "channel",
                    models.CharField(
                        choices=[
                            ("META_FACEBOOK_PAGE", "Meta Facebook Page"),
                            ("META_INSTAGRAM_BUSINESS_ACCOUNT", "Meta Instagram Business Account"),
                        ],
                        max_length=64,
                    ),
                ),
                ("provider_channel_id", models.CharField(max_length=255)),
                ("display_name", models.CharField(blank=True, max_length=255)),
                ("encrypted_access_token", models.TextField()),
                ("token_expires_at", models.DateTimeField(blank=True, null=True)),
                ("granted_scopes", models.JSONField(default=list)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "social_account",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="channel_connections",
                        to="social.socialaccount",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="OAuthState",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("state_digest", models.CharField(max_length=64, unique=True)),
                ("subject", models.CharField(max_length=255)),
                ("expires_at", models.DateTimeField()),
                ("used_at", models.DateTimeField(blank=True, null=True)),
                (
                    "tenant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="oauth_states",
                        to="tenancy.tenant",
                    ),
                ),
            ],
            options={"indexes": [models.Index(fields=["expires_at"], name="oauthstate_expiry_idx")]},
        ),
        migrations.AddConstraint(
            model_name="socialaccount",
            constraint=models.UniqueConstraint(
                fields=("tenant", "provider", "provider_account_id"),
                name="unique_social_account_per_tenant",
            ),
        ),
        migrations.AddConstraint(
            model_name="channelconnection",
            constraint=models.UniqueConstraint(
                fields=("social_account", "channel", "provider_channel_id"),
                name="unique_channel_connection_per_account",
            ),
        ),
    ]
