from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_project_measurement_mode"),
    ]

    operations = [
        migrations.AddField(
            model_name="project",
            name="irradiation_angle_error_seconds",
            field=models.FloatField(blank=True, null=True),
        ),
    ]
