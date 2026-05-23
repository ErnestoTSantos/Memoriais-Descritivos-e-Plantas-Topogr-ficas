from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0006_processrun_planimetric_table"),
    ]

    operations = [
        migrations.RemoveField(model_name="project", name="irradiation_angle_error_seconds"),
        migrations.RemoveField(model_name="project", name="angle_error_limit_seconds"),
        migrations.RemoveField(model_name="project", name="closure_tolerance_m"),
        migrations.RemoveField(model_name="project", name="equipment_linear_error_m"),
        migrations.RemoveField(model_name="project", name="distance_precision_m"),
        migrations.RemoveField(model_name="project", name="angular_precision_seconds"),
        migrations.AlterField(
            model_name="project",
            name="measurement_mode",
            field=models.CharField(
                choices=[
                    ("planimetrico", "Planimetrico (caminhamento)"),
                    ("irradiacao", "Irradiacao (estacao total)"),
                ],
                default="planimetrico",
                max_length=20,
            ),
        ),
        migrations.RemoveField(model_name="processrun", name="accumulated_error_m"),
        migrations.RemoveField(model_name="processrun", name="tolerance_m"),
        migrations.RemoveField(model_name="processrun", name="tolerance_status"),
    ]
