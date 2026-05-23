from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from django.db import transaction
from django.utils.text import slugify

from app.models.schemas import CoordinatePoint
from app.services.processing import ProjectData
from app.services.processing import process_coordinates as process_polygon
from app.services.strategies.export import ExportPayload, ExportStrategyFactory
from core.persistence import save_process_run, store_artifact

BASE_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

EXPORT_FACTORY = ExportStrategyFactory()


@dataclass(frozen=True)
class ExportedFile:
    path: Path
    media_type: str


def export_project_file(
    output_format: str,
    project_data: ProjectData,
    points: list[CoordinatePoint],
    memorial_text: str = "",
    planimetric_table: dict | None = None,
) -> ExportedFile:
    provided_memorial = memorial_text.strip()

    if provided_memorial:
        area_m2 = 0.0
        perimeter_m = 0.0
        closure_error_m = 0.0
        final_memorial_text = provided_memorial
        export_points = points
        final_planimetric_table = planimetric_table or {}
    else:
        result = process_polygon(points, project_data)
        area_m2 = result.area_m2
        perimeter_m = result.perimeter_m
        closure_error_m = result.closure_error_m
        final_memorial_text = result.memorial_text
        export_points = result.points[:-1]
        final_planimetric_table = result.planimetric_table.model_dump()

    slug = slugify(project_data.property_name) or "imovel"
    token = uuid4().hex[:8]
    export_payload = ExportPayload(
        property_name=project_data.property_name,
        points=export_points,
        memorial_text=final_memorial_text,
        output_dir=OUTPUT_DIR,
        slug=slug,
        token=token,
    )

    export_strategy = EXPORT_FACTORY.for_output_format(output_format)
    export_result = export_strategy.export(export_payload)

    with transaction.atomic():
        run = save_process_run(
            project_data,
            export_points,
            area_m2,
            perimeter_m,
            closure_error_m,
            final_planimetric_table,
        )
        store_artifact(export_result.path, output_format, run)

    return ExportedFile(path=export_result.path, media_type=export_result.media_type)
