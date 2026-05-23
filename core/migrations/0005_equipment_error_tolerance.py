from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0004_project_angle_error_limit_seconds"),
    ]

    operations = [
        migrations.AddField(
            model_name="project",
            name="closure_tolerance_m",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="project",
            name="equipment_linear_error_m",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="project",
            name="equipment_angular_error_seconds",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="project",
            name="distance_precision_m",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="project",
            name="angular_precision_seconds",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="processrun",
            name="accumulated_error_m",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="processrun",
            name="tolerance_m",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="processrun",
            name="tolerance_status",
            field=models.CharField(blank=True, default="", max_length=40),
        ),
    ]
