import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("audit", "0001_initial"), ("tenancy", "0002_brand_membership")]

    operations = [
        migrations.AddField(
            model_name="auditlog",
            name="brand",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="audit_logs",
                to="tenancy.brand",
            ),
        ),
    ]
