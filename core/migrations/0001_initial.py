# Generated manually for initial project schema.

import django.contrib.gis.db.models.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Project",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("property_name", models.CharField(max_length=255)),
                ("owner_name", models.CharField(max_length=255)),
                ("municipality", models.CharField(max_length=120)),
                ("state", models.CharField(max_length=2)),
                ("datum", models.CharField(default="SIRGAS2000", max_length=60)),
                ("coordinate_system", models.CharField(default="UTM", max_length=60)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="ProcessRun",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("area_m2", models.FloatField()),
                ("perimeter_m", models.FloatField()),
                ("closure_error_m", models.FloatField()),
                ("status", models.CharField(default="completed", max_length=32)),
                ("executed_at", models.DateTimeField(auto_now_add=True)),
                ("project", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="process_runs", to="core.project")),
            ],
        ),
        migrations.CreateModel(
            name="Vertex",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("vertex_code", models.CharField(max_length=64)),
                ("x_coord", models.FloatField()),
                ("y_coord", models.FloatField()),
                ("seq", models.PositiveIntegerField()),
                ("geom", django.contrib.gis.db.models.fields.PointField(srid=31983)),
                (
                    "process_run",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="vertices", to="core.processrun"),
                ),
            ],
            options={"ordering": ["seq"]},
        ),
        migrations.CreateModel(
            name="Artifact",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("output_format", models.CharField(max_length=10)),
                ("storage_key", models.CharField(max_length=512)),
                ("file_url", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "process_run",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="artifacts", to="core.processrun"),
                ),
            ],
        ),
    ]
