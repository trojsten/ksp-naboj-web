from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ksp_naboj_submission", "0002_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="submission",
            name="judge_public_id",
            field=models.CharField(
                blank=True, db_index=True, default="", max_length=100
            ),
        ),
        migrations.AddField(
            model_name="submission",
            name="protocol_key",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
    ]
