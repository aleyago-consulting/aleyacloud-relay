import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [("tenancy", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="MediaAsset",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("storage_key", models.CharField(max_length=1024, unique=True)),
                ("content_type", models.CharField(max_length=255)),
                ("size_bytes", models.PositiveBigIntegerField()),
                ("checksum", models.CharField(blank=True, max_length=128)),
                (
                    "tenant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="media_assets",
                        to="tenancy.tenant",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Post",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("title", models.CharField(blank=True, max_length=255)),
                ("body", models.TextField(blank=True)),
                (
                    "state",
                    models.CharField(
                        choices=[
                            ("DRAFT", "Draft"),
                            ("PENDING_APPROVAL", "Pending approval"),
                            ("APPROVED", "Approved"),
                            ("SCHEDULED", "Scheduled"),
                            ("PUBLISHING", "Publishing"),
                            ("PUBLISHED", "Published"),
                            ("FAILED", "Failed"),
                            ("CANCELLED", "Cancelled"),
                        ],
                        default="DRAFT",
                        max_length=32,
                    ),
                ),
                ("created_by_subject", models.CharField(blank=True, max_length=255)),
                ("idempotency_key", models.CharField(max_length=255)),
                ("request_fingerprint", models.CharField(max_length=64)),
                (
                    "tenant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="posts",
                        to="tenancy.tenant",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="PostVariant",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("body", models.TextField(blank=True)),
                ("channel_hint", models.CharField(blank=True, max_length=64)),
                (
                    "media_assets",
                    models.ManyToManyField(blank=True, related_name="post_variants", to="content.mediaasset"),
                ),
                (
                    "post",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="variants",
                        to="content.post",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="post",
            constraint=models.UniqueConstraint(
                fields=("tenant", "idempotency_key"), name="unique_post_idempotency_key"
            ),
        ),
    ]
