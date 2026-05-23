from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0005_equipment_error_tolerance"),
    ]

    operations = [
        migrations.AddField(
            model_name="processrun",
            name="planimetric_table",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
