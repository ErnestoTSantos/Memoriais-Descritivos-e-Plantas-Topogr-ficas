from __future__ import annotations

from django.contrib.gis.db import models


class Project(models.Model):
    MEASUREMENT_MODE_CHOICES = (
        ("ponto_a_ponto", "Ponto a ponto"),
        ("irradiacao", "Irradiacao"),
    )

    property_name = models.CharField(max_length=255)
    owner_name = models.CharField(max_length=255)
    municipality = models.CharField(max_length=120)
    state = models.CharField(max_length=2)
    datum = models.CharField(max_length=60, default="SIRGAS2000")
    coordinate_system = models.CharField(max_length=60, default="UTM")
    measurement_mode = models.CharField(max_length=20, choices=MEASUREMENT_MODE_CHOICES, default="ponto_a_ponto")
    irradiation_origin_x = models.FloatField(null=True, blank=True)
    irradiation_origin_y = models.FloatField(null=True, blank=True)
    irradiation_angle_error_seconds = models.FloatField(null=True, blank=True)
    angle_error_limit_seconds = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.property_name} - {self.owner_name}"


class ProcessRun(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="process_runs")
    area_m2 = models.FloatField()
    perimeter_m = models.FloatField()
    closure_error_m = models.FloatField()
    status = models.CharField(max_length=32, default="completed")
    executed_at = models.DateTimeField(auto_now_add=True)


class Vertex(models.Model):
    process_run = models.ForeignKey(ProcessRun, on_delete=models.CASCADE, related_name="vertices")
    vertex_code = models.CharField(max_length=64)
    x_coord = models.FloatField()
    y_coord = models.FloatField()
    seq = models.PositiveIntegerField()
    geom = models.PointField(srid=31983)

    class Meta:
        ordering = ["seq"]


class Artifact(models.Model):
    process_run = models.ForeignKey(ProcessRun, on_delete=models.CASCADE, related_name="artifacts")
    output_format = models.CharField(max_length=10)
    storage_key = models.CharField(max_length=512)
    file_url = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
