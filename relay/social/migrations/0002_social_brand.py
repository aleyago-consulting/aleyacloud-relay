import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("social", "0001_initial"), ("tenancy", "0002_brand_membership")]

    operations = [
        migrations.AddField(
            model_name="socialaccount",
            name="brand",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="social_accounts",
                to="tenancy.brand",
            ),
        ),
        migrations.AddField(
            model_name="oauthstate",
            name="brand",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="oauth_states",
                to="tenancy.brand",
            ),
        ),
    ]
