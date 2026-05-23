from __future__ import annotations

from pathlib import Path

from django.contrib.gis.geos import Point
from django.core.files.storage import default_storage

from app.models.schemas import CoordinatePoint
from app.services.processing import ProjectData
from core.models import Artifact, ProcessRun, Project, Vertex


def save_process_run(
    project_data: ProjectData,
    points: list[CoordinatePoint],
    area: float,
    perimeter: float,
    misclosure: float,
    planimetric_table: dict | None = None,
) -> ProcessRun:
    planimetric_table = planimetric_table or {}

    project = Project.objects.create(
        property_name=project_data.property_name,
        owner_name=project_data.owner_name,
        municipality=project_data.municipality,
        state=project_data.state,
        datum=project_data.datum,
        coordinate_system=project_data.coordinate_system,
        measurement_mode=project_data.measurement_mode,
        irradiation_origin_x=(
            project_data.stations[0].x if project_data.stations else None
        ),
        irradiation_origin_y=(
            project_data.stations[0].y if project_data.stations else None
        ),
        equipment_angular_error_seconds=project_data.equipment_angular_error_seconds,
    )

    run = ProcessRun.objects.create(
        project=project,
        area_m2=area,
        perimeter_m=perimeter,
        closure_error_m=misclosure,
        planimetric_table=planimetric_table,
    )

    for idx, point in enumerate(points[:-1], start=1):
        Vertex.objects.create(
            process_run=run,
            vertex_code=getattr(point, "vertex", "") or getattr(point, "name", ""),
            x_coord=point.x,
            y_coord=point.y,
            seq=idx,
            geom=Point(point.x, point.y, srid=31983),
        )

    return run


def store_artifact(path: Path, output_format: str, run: ProcessRun) -> None:
    with path.open("rb") as fp:
        storage_key = default_storage.save(f"exports/{path.name}", fp)

    try:
        file_url = default_storage.url(storage_key)
    except Exception:
        file_url = ""

    Artifact.objects.create(
        process_run=run,
        output_format=output_format,
        storage_key=storage_key,
        file_url=file_url,
    )
