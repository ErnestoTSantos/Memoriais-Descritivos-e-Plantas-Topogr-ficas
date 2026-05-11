from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="project",
            name="measurement_mode",
            field=models.CharField(
                choices=[("ponto_a_ponto", "Ponto a ponto"), ("irradiacao", "Irradiacao")],
                default="ponto_a_ponto",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="project",
            name="irradiation_origin_x",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="project",
            name="irradiation_origin_y",
            field=models.FloatField(blank=True, null=True),
        ),
    ]
