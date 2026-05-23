from __future__ import annotations

from typing import Any

from rest_framework import serializers

from app.models.schemas import CoordinatePoint
from app.services.processing import ProjectData, build_project_data
from app.services.workflows import ProcessingInput
from core.models import Artifact


class StationSerializer(serializers.Serializer):
    name = serializers.CharField(allow_blank=False)
    x = serializers.FloatField()
    y = serializers.FloatField()


class ProjectDataSerializer(serializers.Serializer):
    property_name = serializers.CharField(required=False, allow_blank=True)
    owner_name = serializers.CharField(required=False, allow_blank=True)
    municipality = serializers.CharField(required=False, allow_blank=True)
    state = serializers.CharField(required=False, allow_blank=True)
    datum = serializers.CharField(required=False, allow_blank=True)
    coordinate_system = serializers.CharField(required=False, allow_blank=True)
    measurement_mode = serializers.CharField(required=False, allow_blank=True)
    stations_json = serializers.CharField(required=False, allow_blank=True)
    irradiation_origin_x = serializers.CharField(required=False, allow_blank=True)
    irradiation_origin_y = serializers.CharField(required=False, allow_blank=True)
    equipment_angular_error_seconds = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    def build_project_data(self) -> ProjectData:
        return build_project_data(self.validated_data)


class TraverseObservationSerializer(serializers.Serializer):
    station = serializers.CharField(required=False, allow_blank=True)
    sighted_point = serializers.CharField(required=False, allow_blank=True)
    distance_m = serializers.FloatField()
    observed_angle_deg = serializers.FloatField()
    observed_angle_dms = serializers.CharField(required=False, allow_blank=True)


class IrradiationObservationSerializer(serializers.Serializer):
    vertex = serializers.CharField(required=False, allow_blank=True)
    sighted_point = serializers.CharField(required=False, allow_blank=True)
    distance_m = serializers.FloatField()
    azimuth_deg = serializers.FloatField(required=False)
    observed_angle_deg = serializers.FloatField(required=False)
    station = serializers.CharField(required=False, allow_blank=True)
    station_name = serializers.CharField(required=False, allow_blank=True)
    station_x = serializers.FloatField(required=False)
    station_y = serializers.FloatField(required=False)


class ProcessingRequestSerializer(ProjectDataSerializer):
    file = serializers.FileField(required=False, allow_empty_file=False)
    coordinates_text = serializers.CharField(required=False, allow_blank=True)
    traverse_observations = serializers.CharField(required=False, allow_blank=True)
    initial_azimuth_deg = serializers.FloatField(required=False, default=0.0)

    def build_processing_input(self) -> ProcessingInput:
        uploaded_file = self.validated_data.get("file")
        return ProcessingInput(
            file_name=getattr(uploaded_file, "name", "") if uploaded_file else "",
            file_content=uploaded_file.read() if uploaded_file else None,
            coordinates_text=self.validated_data.get("coordinates_text", ""),
            traverse_observations_json=self.validated_data.get(
                "traverse_observations", ""
            ),
            initial_azimuth_deg=self.validated_data.get("initial_azimuth_deg", 0.0),
        )


class CoordinatePointSerializer(serializers.Serializer):
    vertex = serializers.CharField()
    x = serializers.FloatField()
    y = serializers.FloatField()

    def to_coordinate_point(self, value: dict[str, Any]) -> CoordinatePoint:
        return CoordinatePoint(**value)


class ExportRequestSerializer(ProjectDataSerializer):
    points = CoordinatePointSerializer(many=True)
    memorial_text = serializers.CharField(required=False, allow_blank=True)
    planimetric_table = serializers.DictField(required=False)

    def build_points(self) -> list[CoordinatePoint]:
        return [CoordinatePoint(**point) for point in self.validated_data["points"]]


class ProcessingResponseSerializer(serializers.Serializer):
    points = serializers.ListField()
    adjusted_points = serializers.ListField()
    area_m2 = serializers.FloatField()
    perimeter_m = serializers.FloatField()
    closure_error_m = serializers.FloatField()
    adjustment_summary = serializers.DictField()
    segments = serializers.ListField()
    planimetric_segments = serializers.ListField()
    planimetric_table = serializers.DictField()
    irradiation_table = serializers.DictField(required=False, allow_null=True)
    memorial_text = serializers.CharField()
    measurement_mode = serializers.CharField()
    stations = StationSerializer(many=True)
    equipment_angular_error_seconds = serializers.FloatField(
        required=False,
        allow_null=True,
    )
    traverse_angular_summary = serializers.DictField(required=False, allow_null=True)


class ArtifactSerializer(serializers.ModelSerializer):
    format = serializers.CharField(source="output_format")
    project = serializers.CharField(source="process_run.project.property_name")

    class Meta:
        model = Artifact
        fields = (
            "id",
            "format",
            "storage_key",
            "file_url",
            "created_at",
            "project",
        )
