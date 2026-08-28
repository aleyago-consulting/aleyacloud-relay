from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("content", "0002_post_media_brand")]

    operations = [
        migrations.AddField(
            model_name="mediaasset",
            name="upload_state",
            field=models.CharField(
                choices=[
                    ("PENDING", "Pending upload"),
                    ("READY", "Ready"),
                    ("FAILED", "Upload failed"),
                ],
                # Existing assets predate upload confirmation and must remain usable.
                default="READY",
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name="mediaasset",
            name="upload_state",
            field=models.CharField(
                choices=[
                    ("PENDING", "Pending upload"),
                    ("READY", "Ready"),
                    ("FAILED", "Upload failed"),
                ],
                default="PENDING",
                max_length=16,
            ),
        ),
    ]
