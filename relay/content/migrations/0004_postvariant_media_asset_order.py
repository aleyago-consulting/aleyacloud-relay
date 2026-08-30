from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("content", "0003_mediaasset_upload_state")]

    operations = [
        migrations.AddField(
            model_name="postvariant",
            name="media_asset_order",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
