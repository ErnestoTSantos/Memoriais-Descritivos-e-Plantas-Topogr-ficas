from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from typing import Any

from app.models.schemas import (
    CoordinatePoint,
    IrradiationObservation,
    IrradiationTable,
    PlanimetricCalculationTable,
    SegmentInfo,
    TraverseAngularSummary,
    TraverseObservation,
)
from app.services.angles import decimal_to_dms
from app.services.geometry import (
    EPSILON,
    build_segments,
    closure_error,
    ensure_closed,
    is_closed,
    polygon_area,
    polygon_perimeter,
    validate_no_self_intersection,
    validate_points,
)
from app.services.irradiation import compute_irradiation
from app.services.planimetric import build_planimetric_calculation_table
from app.services.planimetry import PlanimetryLeg, compute_planimetry_traverse
from app.services.reports import generate_memorial_text
from app.services.tolerances import (
    EquipmentErrorConfig,
    build_linear_adjustment_diagnostics,
    enrich_irradiation_diagnostics,
)


@dataclass(frozen=True)
class Station:
    name: str
    x: float
    y: float


@dataclass(frozen=True)
class ProjectData:
    property_name: str
    owner_name: str
    municipality: str
    state: str
    datum: str
    coordinate_system: str
    measurement_mode: str

    stations: list[Station]

    equipment_angular_error_seconds: float | None


@dataclass(frozen=True)
class ProcessingResult:
    points: list[CoordinatePoint]
    adjusted_points: list[CoordinatePoint]
    segments: list[SegmentInfo]
    planimetric_table: PlanimetricCalculationTable
    area_m2: float
    perimeter_m: float
    closure_error_m: float
    adjustment_summary: dict[str, Any]
    memorial_text: str
    irradiation_table: IrradiationTable | None = None
    traverse_angular_summary: TraverseAngularSummary | None = None


RESIDUAL_CLOSURE_RATIO = 0.05


def parse_angle(value) -> float:
    if isinstance(value, (int, float)):
        return float(value) % 360

    text = str(value).strip().replace(",", ".")

    gms_pattern = r"(\d+)[°\s]+(\d+)[\'\s]+(\d+(?:\.\d+)?)"
    match = re.search(gms_pattern, text)

    if match:
        g, m, s = match.groups()
        return (float(g) + float(m) / 60 + float(s) / 3600) % 360

    return float(text) % 360


def validate_irradiation_input(observations: list[IrradiationObservation]) -> None:
    for obs in observations:
        distance_m = float(obs.distance_m)
        azimuth_deg = float(obs.azimuth_deg)
        if not math.isfinite(distance_m) or distance_m <= 0:
            raise ValueError(f"Distância inválida para o ponto {obs.vertex}")
        if not math.isfinite(azimuth_deg):
            raise ValueError(f"Azimute inválido para o ponto {obs.vertex}")


def _observation_has_station(obs: IrradiationObservation) -> bool:
    return obs.station_x is not None and obs.station_y is not None


def _same_vertex_label(first: CoordinatePoint, last: CoordinatePoint) -> bool:
    first_label = (first.vertex or "").strip().upper()
    last_label = (last.vertex or "").strip().upper()
    return bool(first_label and last_label and first_label == last_label)


def _median_positive_segment_length(points: list[CoordinatePoint]) -> float:
    lengths = sorted(
        math.hypot(points[i + 1].x - points[i].x, points[i + 1].y - points[i].y)
        for i in range(len(points) - 1)
    )
    lengths = [
        length for length in lengths if math.isfinite(length) and length > EPSILON
    ]
    if not lengths:
        return 0.0

    middle = len(lengths) // 2
    if len(lengths) % 2:
        return lengths[middle]
    return (lengths[middle - 1] + lengths[middle]) / 2.0


def _is_residual_closure_candidate(points: list[CoordinatePoint]) -> bool:
    """Return True when the last point looks like a measured closing residual."""
    if len(points) < 2 or is_closed(points[0], points[-1]):
        return False

    if _same_vertex_label(points[0], points[-1]):
        return True

    gap = closure_error(points)
    reference_length = _median_positive_segment_length(points)
    if reference_length <= EPSILON:
        return False

    return gap <= (reference_length * RESIDUAL_CLOSURE_RATIO)


def build_project_data(raw):

    def parse_float(v):
        if v is None:
            return None
        text = str(v).strip()
        if text == "":
            return None
        value = float(text.replace(",", "."))
        if not math.isfinite(value):
            raise ValueError("Valores numericos do projeto devem ser finitos.")
        return value

    equipment_angular_error = parse_float(
        raw.get("equipment_angular_error_seconds")
        or raw.get("equipment_angular_error")
    )

    if equipment_angular_error is not None and equipment_angular_error <= 0:
        raise ValueError("O erro angular do equipamento deve ser maior que zero.")

    stations: list[Station] = []

    stations_json_str = str(raw.get("stations_json") or "").strip()
    if stations_json_str:
        try:
            stations_raw = json.loads(stations_json_str)
        except Exception as exc:
            raise ValueError(f"Formato invalido em stations_json: {exc}") from exc

        seen_names: set[str] = set()
        for s in stations_raw:
            sname = str(s.get("name") or "").strip()
            if not sname:
                raise ValueError("Nome da estacao nao pode ser vazio.")
            if sname in seen_names:
                raise ValueError(f"Nome de estacao duplicado: '{sname}'.")
            seen_names.add(sname)
            sx = parse_float(s.get("x"))
            sy = parse_float(s.get("y"))
            if sx is None or sy is None:
                raise ValueError(f"Estacao '{sname}': informe X e Y.")
            stations.append(Station(name=sname, x=sx, y=sy))
    else:
        origin_x = parse_float(raw.get("irradiation_origin_x"))
        origin_y = parse_float(raw.get("irradiation_origin_y"))

        if (origin_x is None) != (origin_y is None):
            raise ValueError(
                "Informe X e Y da estacao de irradiacao, ou deixe ambos em branco."
            )

        origin_station_name = (
            str(raw.get("irradiation_origin_station") or "").strip()
            or "A"
        )
        if origin_x is not None and origin_y is not None:
            stations.append(
                Station(
                    name=origin_station_name,
                    x=origin_x,
                    y=origin_y,
                )
            )

    mode_raw = str(raw.get("measurement_mode", "")).lower()
    if "irradiacao" in mode_raw:
        mode = "irradiacao"
    else:
        mode = "planimetrico"

    return ProjectData(
        property_name=raw.get("property_name", "Imovel"),
        owner_name=raw.get("owner_name", "Proprietario"),
        municipality=raw.get("municipality", "Municipio"),
        state=(raw.get("state") or "UF").upper()[:2],
        datum=raw.get("datum", "SIRGAS2000"),
        coordinate_system=raw.get("coordinate_system", "UTM"),
        measurement_mode=mode,
        stations=stations,
        equipment_angular_error_seconds=equipment_angular_error,
    )


def _equipment_config(project_data: ProjectData) -> EquipmentErrorConfig:
    return EquipmentErrorConfig(
        linear_error_m=None,
        angular_error_seconds=project_data.equipment_angular_error_seconds,
        distance_precision_m=None,
        angular_precision_seconds=None,
        closure_tolerance_m=None,
        angle_error_limit_seconds=None,
        measured_angular_error_seconds=None,
    )


def _deviation_from_nearest_minute_seconds(angle_deg: float) -> float:
    """Return the absolute angular deviation from the closest whole minute."""

    total_seconds = (float(angle_deg) % 360.0) * 3600.0
    nearest_minute_seconds = round(total_seconds / 60.0) * 60.0
    return abs(total_seconds - nearest_minute_seconds)


def _max_irradiation_observed_deviation_seconds(
    observations: list[IrradiationObservation],
) -> float:
    if not observations:
        return 0.0
    return max(
        _deviation_from_nearest_minute_seconds(obs.azimuth_deg)
        for obs in observations
    )


def process_traverse(
    observations: list[TraverseObservation],
    project_data: ProjectData,
    *,
    initial_azimuth_deg: float = 0.0,
) -> ProcessingResult:
    """Process a planimetric traverse from observed angles and distances."""
    if len(observations) < 3:
        raise ValueError("Informe ao menos 3 lados para calcular a poligonal.")

    for obs in observations:
        if not math.isfinite(obs.distance_m) or obs.distance_m <= 0:
            raise ValueError(
                f"Distância inválida na linha {obs.station}→{obs.sighted_point}"
            )
        if not math.isfinite(obs.observed_angle_deg):
            raise ValueError(
                f"Ângulo inválido na linha {obs.station}→{obs.sighted_point}"
            )

    legs = [
        PlanimetryLeg(
            start_vertex=obs.station,
            end_vertex=obs.sighted_point,
            distance_m=obs.distance_m,
            adjusted_angle_deg=obs.observed_angle_deg,
        )
        for obs in observations
    ]

    result = compute_planimetry_traverse(
        legs,
        initial_azimuth_deg=initial_azimuth_deg,
        balance_angular_closure=True,
        minimize_projection_closure=False,
    )

    n = len(legs)
    misclosure_s = result.angular_misclosure_seconds
    correction_s = result.applied_angle_correction_seconds

    eq_angular_error = project_data.equipment_angular_error_seconds
    if eq_angular_error is not None and eq_angular_error > 0:
        allowed_s = eq_angular_error * n
        if abs(misclosure_s) <= allowed_s:
            ang_status = "ok"
            ang_label = f"Dentro da tolerância ({abs(misclosure_s):.2f}\" ≤ {allowed_s:.2f}\")"
        else:
            ang_status = "warning"
            ang_label = (
                "Erro angular acima da precisão informada do equipamento. "
                "Revise as observações."
            )
    else:
        allowed_s = None
        ang_status = "nao_informado"
        ang_label = "Erro angular do equipamento não informado"

    angular_summary = TraverseAngularSummary(
        n_sides=n,
        angular_misclosure_seconds=misclosure_s,
        allowed_error_seconds=allowed_s,
        correction_per_side_seconds=correction_s,
        status=ang_status,
        status_label=ang_label,
    )

    segments: list[SegmentInfo] = []
    for i, seg in enumerate(result.segments):
        azimuth_dms = decimal_to_dms(seg.azimuth_deg)
        segments.append(
            SegmentInfo(
                start_vertex=seg.start_vertex,
                end_vertex=seg.end_vertex,
                distance_m=seg.distance_m,
                azimuth_deg=seg.azimuth_deg,
                azimuth_dms=azimuth_dms,
                bearing=seg.bearing,
                observed_angle_deg=observations[i].observed_angle_deg,
                delta_e_m=seg.delta_e_m,
                delta_n_m=seg.delta_n_m,
                correction_e_m=seg.correction_e_m,
                correction_n_m=seg.correction_n_m,
                adjusted_delta_e_m=seg.adjusted_delta_e_m,
                adjusted_delta_n_m=seg.adjusted_delta_n_m,
                applied_angle_error_seconds=correction_s,
                contribution_percent=(seg.distance_m / result.perimeter_m * 100)
                if result.perimeter_m > 0
                else 0.0,
                contribution_status="baixa",
            )
        )

    adjusted_points = list(result.adjusted_points)
    raw_points = list(result.raw_points)

    adjustment_summary: dict[str, Any] = {
        "closure_dx_m": result.closure_dx_m,
        "closure_dy_m": result.closure_dy_m,
        "linear_closure_error_m": result.closure_error_m,
        "accumulated_error_m": result.closure_error_m,
        "correction_sum_e_m": -result.closure_dx_m,
        "correction_sum_n_m": -result.closure_dy_m,
        "adjustment_method": "bowditch_linear_proporcional",
        "status": "dentro_da_tolerancia",
        "status_label": "dentro da tolerância",
        "angular_misclosure_seconds": misclosure_s,
        "angular_correction_per_side_seconds": correction_s,
        "angular_tolerance_seconds": allowed_s,
        "angular_status": ang_status,
        "angular_status_label": ang_label,
        "messages": (
            [ang_label]
            if ang_status == "warning"
            else []
        ),
    }

    survey_points = adjusted_points

    planimetric_table = build_planimetric_calculation_table(
        survey_points=survey_points,
        adjusted_points=adjusted_points,
        segments=segments,
        adjustment_summary=adjustment_summary,
        area_m2=result.area_m2,
        perimeter_m=result.perimeter_m,
    )

    memorial_text = generate_memorial_text(
        property_name=project_data.property_name,
        owner_name=project_data.owner_name,
        municipality=project_data.municipality,
        state=project_data.state,
        datum=project_data.datum,
        coordinate_system=project_data.coordinate_system,
        measurement_mode=project_data.measurement_mode,
        irradiation_origin_x=None,
        irradiation_origin_y=None,
        irradiation_angle_error_seconds=None,
        area_m2=result.area_m2,
        perimeter_m=result.perimeter_m,
        segments=segments,
    )

    closed_points = list(adjusted_points)
    if len(closed_points) >= 2 and not is_closed(closed_points[0], closed_points[-1]):
        closed_points.append(
            CoordinatePoint(
                vertex=closed_points[0].vertex,
                x=closed_points[0].x,
                y=closed_points[0].y,
            )
        )

    return ProcessingResult(
        points=closed_points,
        adjusted_points=adjusted_points,
        segments=segments,
        planimetric_table=planimetric_table,
        area_m2=result.area_m2,
        perimeter_m=result.perimeter_m,
        closure_error_m=result.closure_error_m,
        adjustment_summary=adjustment_summary,
        memorial_text=memorial_text,
        irradiation_table=None,
        traverse_angular_summary=angular_summary,
    )


def process_coordinates(points, project_data):
    irradiation_observations: list[IrradiationObservation] | None = None
    irradiation_table: IrradiationTable | None = None
    default_station = None

    if project_data.measurement_mode == "irradiacao":
        irradiation_observations = list(points)

        has_station_in_observations = any(
            _observation_has_station(obs) for obs in points
        )
        if not project_data.stations and not has_station_in_observations:
            raise ValueError("Nenhuma estação informada")

        validate_irradiation_input(points)
        default_station = project_data.stations[0] if project_data.stations else None

        stations_dict: dict[str, tuple[float, float]] | None = (
            {s.name: (s.x, s.y) for s in project_data.stations}
            if project_data.stations
            else None
        )

        points, irradiation_table = compute_irradiation(
            points,
            origin_x=default_station.x if default_station else None,
            origin_y=default_station.y if default_station else None,
            angle_error_seconds=project_data.equipment_angular_error_seconds or 0.0,
            stations=stations_dict,
        )

    validate_points(points)

    residual_closure = _is_residual_closure_candidate(points)
    misclosure = closure_error(points) if residual_closure else 0.0
    closure_dx = points[-1].x - points[0].x if residual_closure else 0.0
    closure_dy = points[-1].y - points[0].y if residual_closure else 0.0

    closed_points = ensure_closed(points)

    validate_no_self_intersection(closed_points)

    area = polygon_area(closed_points)
    if area <= 0:
        raise ValueError("Poligono invalido: area deve ser maior que zero.")

    survey_points = points if residual_closure else closed_points

    # Irradiation coordinates already include the angular correction.
    angle_err = (
        0.0
        if project_data.measurement_mode == "irradiacao"
        else (project_data.equipment_angular_error_seconds or 0.0)
    )
    segments = build_segments(survey_points, angle_error_seconds=angle_err)

    perimeter = polygon_perimeter(survey_points)
    adjusted_points, segments, adjustment_summary = build_linear_adjustment_diagnostics(
        survey_points=survey_points,
        segments=segments,
        config=_equipment_config(project_data),
        closure_dx_m=closure_dx,
        closure_dy_m=closure_dy,
        closure_error_m=misclosure,
        perimeter_m=perimeter,
        area_m2=area,
        residual_closure=residual_closure,
    )

    if project_data.measurement_mode == "irradiacao" and irradiation_observations:
        observed_angular_deviation_seconds = (
            _max_irradiation_observed_deviation_seconds(irradiation_observations)
        )
        adjusted_points, adjustment_summary = enrich_irradiation_diagnostics(
            observations=irradiation_observations,
            adjusted_points=adjusted_points,
            config=_equipment_config(project_data),
            default_station_x=default_station.x if default_station else None,
            default_station_y=default_station.y if default_station else None,
            applied_angle_error_seconds=observed_angular_deviation_seconds,
            summary=adjustment_summary,
        )
        adjustment_summary["observed_angular_deviation_seconds"] = (
            observed_angular_deviation_seconds
        )
        if (
            project_data.equipment_angular_error_seconds is not None
            and observed_angular_deviation_seconds
            > project_data.equipment_angular_error_seconds
        ):
            adjustment_summary.setdefault("messages", []).append(
                "Erro angular acima da precisão informada do equipamento. Revise as observações."
            )

    planimetric_table = build_planimetric_calculation_table(
        survey_points=survey_points,
        adjusted_points=adjusted_points,
        segments=segments,
        adjustment_summary=adjustment_summary,
        area_m2=area,
        perimeter_m=perimeter,
    )

    memorial_text = generate_memorial_text(
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
        irradiation_angle_error_seconds=None,
        area_m2=area,
        perimeter_m=perimeter,
        segments=segments,
    )

    return ProcessingResult(
        points=closed_points,
        adjusted_points=adjusted_points,
        segments=segments,
        planimetric_table=planimetric_table,
        area_m2=area,
        perimeter_m=perimeter,
        closure_error_m=misclosure,
        adjustment_summary=adjustment_summary,
        memorial_text=memorial_text,
        irradiation_table=irradiation_table,
    )
