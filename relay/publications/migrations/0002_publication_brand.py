import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("publications", "0001_initial"),
        ("tenancy", "0002_brand_membership"),
    ]

    operations = [
        migrations.AddField(
            model_name="publication",
            name="brand",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="publications",
                to="tenancy.brand",
            ),
        ),
    ]
