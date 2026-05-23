from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.models.schemas import (
    CoordinatePoint,
    IrradiationObservation,
    TraverseObservation,
)
from app.services.processing import ProjectData, ProcessingResult
from app.services.processing import process_coordinates as process_polygon
from app.services.processing import process_traverse
from app.services.strategies.parsing import ParsingStrategyFactory


@dataclass(frozen=True)
class ProcessingInput:
    file_name: str = ""
    file_content: bytes | None = None
    coordinates_text: str = ""
    traverse_observations_json: str = ""
    initial_azimuth_deg: float = 0.0


PARSING_FACTORY = ParsingStrategyFactory()


def process_project_input(
    project_data: ProjectData,
    processing_input: ProcessingInput,
) -> ProcessingResult:
    if project_data.measurement_mode == "planimetrico":
        return _process_traverse_input(project_data, processing_input)

    if project_data.measurement_mode == "irradiacao":
        return _process_irradiation_input(project_data, processing_input)

    raise ValueError(f"Modalidade desconhecida: {project_data.measurement_mode}")


def build_result_payload(
    result: ProcessingResult,
    project_data: ProjectData,
) -> dict[str, Any]:
    planimetric_table = result.planimetric_table.model_dump()
    planimetric_rows = planimetric_table.get("segments", [])
    segment_payload = [
        {
            **(planimetric_rows[index] if index < len(planimetric_rows) else {}),
            **segment.model_dump(),
        }
        for index, segment in enumerate(result.segments)
    ]

    return {
        "points": [point.model_dump() for point in result.points],
        "adjusted_points": [point.model_dump() for point in result.adjusted_points],
        "area_m2": result.area_m2,
        "perimeter_m": result.perimeter_m,
        "closure_error_m": result.closure_error_m,
        "adjustment_summary": result.adjustment_summary,
        "segments": segment_payload,
        "planimetric_segments": planimetric_rows,
        "planimetric_table": planimetric_table,
        "irradiation_table": (
            result.irradiation_table.model_dump() if result.irradiation_table else None
        ),
        "memorial_text": result.memorial_text,
        "measurement_mode": project_data.measurement_mode,
        "stations": [
            {"name": s.name, "x": s.x, "y": s.y}
            for s in getattr(project_data, "stations", [])
        ],
        "equipment_angular_error_seconds": project_data.equipment_angular_error_seconds,
        "traverse_angular_summary": (
            result.traverse_angular_summary.model_dump()
            if result.traverse_angular_summary
            else None
        ),
    }


def _process_traverse_input(
    project_data: ProjectData,
    processing_input: ProcessingInput,
) -> ProcessingResult:
    if not processing_input.traverse_observations_json.strip():
        raise ValueError(
            "Informe os dados do caminhamento (estação, ponto, distância, ângulo)."
        )

    observations_raw = json.loads(processing_input.traverse_observations_json)
    observations = [TraverseObservation(**row) for row in observations_raw]
    return process_traverse(
        observations,
        project_data,
        initial_azimuth_deg=processing_input.initial_azimuth_deg,
    )


def _process_irradiation_input(
    project_data: ProjectData,
    processing_input: ProcessingInput,
) -> ProcessingResult:
    points = _parse_irradiation_observations(processing_input)

    has_station_in_observations = any(
        getattr(obs, "station_x", None) is not None
        and getattr(obs, "station_y", None) is not None
        for obs in points
    )
    if not project_data.stations and not has_station_in_observations:
        raise ValueError("Informe pelo menos uma estação para irradiação.")

    return process_polygon(points, project_data)


def _parse_irradiation_observations(
    processing_input: ProcessingInput,
) -> list[IrradiationObservation]:
    if processing_input.traverse_observations_json.strip():
        observations_raw = json.loads(processing_input.traverse_observations_json)
        return [
            IrradiationObservation(
                vertex=str(row.get("sighted_point") or row.get("vertex") or ""),
                azimuth_deg=float(row.get("observed_angle_deg") or 0),
                distance_m=float(row.get("distance_m") or 0),
                station_name=str(row.get("station") or "") or None,
            )
            for row in observations_raw
        ]

    if processing_input.file_content and processing_input.file_name:
        parsing_strategy = PARSING_FACTORY.for_irradiation_upload_name(
            processing_input.file_name
        )
        return parsing_strategy.parse(processing_input.file_content)

    if not processing_input.coordinates_text.strip():
        raise ValueError(
            "Informe observacoes de irradiacao pela tabela ou por arquivo."
        )

    return PARSING_FACTORY.for_irradiation_text().parse(
        processing_input.coordinates_text
    )
