import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("content", "0001_initial"), ("tenancy", "0002_brand_membership")]

    operations = [
        migrations.AddField(
            model_name="post",
            name="brand",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="posts",
                to="tenancy.brand",
            ),
        ),
        migrations.AddField(
            model_name="mediaasset",
            name="brand",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="media_assets",
                to="tenancy.brand",
            ),
        ),
    ]
