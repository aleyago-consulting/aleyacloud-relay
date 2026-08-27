import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [("content", "0002_post_media_brand"), ("tenancy", "0002_brand_membership")]

    operations = [
        migrations.CreateModel(
            name="ApprovalRequest",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("requested_by_subject", models.CharField(max_length=255)),
                ("token_digest", models.CharField(max_length=64, unique=True)),
                ("expires_at", models.DateTimeField()),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("decided_at", models.DateTimeField(blank=True, null=True)),
                ("decision", models.CharField(choices=[("PENDING", "Pending"), ("APPROVED", "Approved"), ("CHANGES_REQUESTED", "Changes requested")], default="PENDING", max_length=32)),
                ("brand", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="approval_requests", to="tenancy.brand")),
                ("post", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="approval_requests", to="content.post")),
            ],
        ),
        migrations.CreateModel(
            name="ApprovalComment",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("author_label", models.CharField(blank=True, max_length=255)),
                ("body", models.TextField()),
                ("approval_request", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="comments", to="approvals.approvalrequest")),
            ],
        ),
    ]
