from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0003_project_irradiation_angle_error_seconds"),
    ]

    operations = [
        migrations.AddField(
            model_name="project",
            name="angle_error_limit_seconds",
            field=models.FloatField(blank=True, null=True),
        ),
    ]
