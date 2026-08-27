import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [("tenancy", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="AuditLog",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("actor_type", models.CharField(max_length=64)),
                ("actor_id", models.CharField(max_length=255)),
                ("event_type", models.CharField(max_length=100)),
                ("subject_type", models.CharField(max_length=100)),
                ("subject_id", models.UUIDField()),
                ("metadata", models.JSONField(default=dict)),
                (
                    "tenant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="audit_logs",
                        to="tenancy.tenant",
                    ),
                ),
            ],
            options={
                "indexes": [models.Index(fields=["tenant", "created_at"], name="auditlog_tenant_created_idx")],
            },
        ),
    ]

