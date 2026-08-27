import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("tenancy", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="Brand",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("slug", models.SlugField()),
                ("name", models.CharField(max_length=200)),
                ("timezone", models.CharField(default="UTC", max_length=64)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "workspace",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="brands",
                        to="tenancy.tenant",
                    ),
                ),
            ],
            options={"ordering": ("name",)},
        ),
        migrations.CreateModel(
            name="Membership",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("subject", models.CharField(max_length=255)),
                (
                    "role",
                    models.CharField(
                        choices=[
                            ("OWNER", "Workspace owner"),
                            ("MANAGER", "Agency manager"),
                            ("CONTENT_CREATOR", "Content creator"),
                            ("CLIENT_APPROVER", "Client approver"),
                            ("VIEWER", "Viewer"),
                        ],
                        max_length=32,
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                (
                    "workspace",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="memberships",
                        to="tenancy.tenant",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="brand",
            constraint=models.UniqueConstraint(
                fields=("workspace", "slug"), name="unique_brand_slug_per_workspace"
            ),
        ),
        migrations.AddConstraint(
            model_name="membership",
            constraint=models.UniqueConstraint(
                fields=("workspace", "subject"), name="unique_workspace_membership"
            ),
        ),
    ]
