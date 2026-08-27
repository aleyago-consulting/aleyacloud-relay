import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("content", "0001_initial"),
        ("social", "0001_initial"),
        ("tenancy", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Publication",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("scheduled_for", models.DateTimeField()),
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
                ("idempotency_key", models.CharField(max_length=255)),
                ("request_fingerprint", models.CharField(max_length=64)),
                ("provider_publication_id", models.CharField(blank=True, max_length=255)),
                ("last_error_code", models.CharField(blank=True, max_length=100)),
                ("last_error_message", models.TextField(blank=True)),
                (
                    "channel_connection",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="publications",
                        to="social.channelconnection",
                    ),
                ),
                (
                    "post_variant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="publications",
                        to="content.postvariant",
                    ),
                ),
                (
                    "tenant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="publications",
                        to="tenancy.tenant",
                    ),
                ),
            ],
            options={
                "indexes": [models.Index(fields=["state", "scheduled_for"], name="publication_state_sched_idx")],
            },
        ),
        migrations.CreateModel(
            name="PublicationAttempt",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("attempt_number", models.PositiveIntegerField()),
                ("started_at", models.DateTimeField()),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("outcome", models.CharField(blank=True, max_length=32)),
                ("provider_status_code", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("error_code", models.CharField(blank=True, max_length=100)),
                ("error_message", models.TextField(blank=True)),
                (
                    "publication",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attempts",
                        to="publications.publication",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="publication",
            constraint=models.UniqueConstraint(
                fields=("tenant", "idempotency_key"), name="unique_publication_idempotency_key"
            ),
        ),
        migrations.AddConstraint(
            model_name="publicationattempt",
            constraint=models.UniqueConstraint(
                fields=("publication", "attempt_number"), name="unique_publication_attempt_number"
            ),
        ),
    ]
