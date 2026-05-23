from __future__ import annotations

import math
from typing import Any

from app.models.schemas import (
    CoordinatePoint,
    PlanimetricCalculationSummary,
    PlanimetricCalculationTable,
    PlanimetricTableRow,
    SegmentInfo,
)
from app.services.angles import decimal_to_dms


PLANIMETRIC_FORMULAS = {
    "projecao_e": "DeltaE = distancia * sen(azimute)",
    "projecao_n": "DeltaN = distancia * cos(azimute)",
    "separacao_leste_oeste": "E(+) = max(DeltaE, 0); W(-) = min(DeltaE, 0)",
    "separacao_norte_sul": "N(+) = max(DeltaN, 0); S(-) = min(DeltaN, 0)",
    "fechamento_linear": "erro_linear = sqrt(erro_E^2 + erro_N^2)",
    "bowditch_x": "Cx_i = -erro_E * (distancia_i / perimetro)",
    "bowditch_y": "Cy_i = -erro_N * (distancia_i / perimetro)",
    "projecao_ajustada_x": "DeltaE_ajustado_i = DeltaE_i + Cx_i",
    "projecao_ajustada_y": "DeltaN_ajustado_i = DeltaN_i + Cy_i",
    "coordenada_acumulada_x": "X_i = X_inicial + soma(DeltaE_ajustado)",
    "coordenada_acumulada_y": "Y_i = Y_inicial + soma(DeltaN_ajustado)",
    "contribuicao": "contribuicao_i = distancia_i / perimetro * 100",
    "ajuste_angular": "angulo_corrigido = angulo_observado + ajuste_angular",
}


def _finite_or_zero(value: Any) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    return numeric if math.isfinite(numeric) else 0.0


def _coord_x(point: CoordinatePoint) -> float:
    return _finite_or_zero(
        point.adjusted_x if point.adjusted_x is not None else point.x
    )


def _coord_y(point: CoordinatePoint) -> float:
    return _finite_or_zero(
        point.adjusted_y if point.adjusted_y is not None else point.y
    )


def _format_seconds(seconds: float) -> str:
    sign = "+" if seconds >= 0.0 else "-"
    return f'{sign}{abs(seconds):.2f}"'


def _status_severity(status: str) -> str:
    if status == "alta":
        return "danger"
    if status == "moderada":
        return "warning"
    return "success"


def _observed_angle_deg(segments: list[SegmentInfo], index: int) -> float | None:
    """Return the clockwise angle at the row station from adjacent azimuths.

    The current project receives coordinates or azimuth/distance observations,
    not a field book with measured interior angles.  Therefore this value is
    derived from geometry:

    back_azimuth = azimuth(previous_segment) + 180 degrees
    observed_angle = azimuth(current_segment) - back_azimuth

    The result is normalized to [0, 360), preserving the traverse direction.
    """

    if len(segments) < 2:
        return None

    previous = segments[index - 1]
    current = segments[index]
    back_azimuth = (previous.azimuth_deg + 180.0) % 360.0
    return (current.azimuth_deg - back_azimuth + 360.0) % 360.0


def _segment_delta(
    segment: SegmentInfo, start: CoordinatePoint, end: CoordinatePoint
) -> tuple[float, float]:
    delta_x = _finite_or_zero(segment.delta_e_m)
    delta_y = _finite_or_zero(segment.delta_n_m)
    if delta_x == 0.0 and delta_y == 0.0:
        return end.x - start.x, end.y - start.y
    return delta_x, delta_y


def build_planimetric_calculation_table(
    *,
    survey_points: list[CoordinatePoint],
    adjusted_points: list[CoordinatePoint],
    segments: list[SegmentInfo],
    adjustment_summary: dict[str, Any],
    area_m2: float,
    perimeter_m: float,
) -> PlanimetricCalculationTable:
    """Build the complete auditable planimetric calculation table.

    This function intentionally separates raw, corrected, adjusted and
    accumulated values:

    raw values
        Distance, observed angle, azimuth, DeltaE and DeltaN.
    corrected values
        Angle corrected by the configured angular adjustment.
    adjusted values
        DeltaE/DeltaN after Bowditch correction.
    accumulated values
        Running adjusted coordinates at the end of each segment.
    """

    rows: list[PlanimetricTableRow] = []
    closure_error_x = _finite_or_zero(adjustment_summary.get("closure_dx_m"))
    closure_error_y = _finite_or_zero(adjustment_summary.get("closure_dy_m"))

    for index, segment in enumerate(segments):
        start = survey_points[index]
        end = survey_points[index + 1]
        adjusted_start = (
            adjusted_points[index] if index < len(adjusted_points) else start
        )
        adjusted_end = (
            adjusted_points[index + 1] if index + 1 < len(adjusted_points) else end
        )

        # Display deltas must come from the true azimuth, not from projection
        # azimuths that may be flipped internally for closure minimisation.
        _az_rad = math.radians(segment.azimuth_deg)
        delta_x = segment.distance_m * math.sin(_az_rad)
        delta_y = segment.distance_m * math.cos(_az_rad)
        correction_x = _finite_or_zero(segment.correction_e_m)
        correction_y = _finite_or_zero(segment.correction_n_m)
        # Adjusted display values inherit the true azimuth sign convention.
        adjusted_delta_x = delta_x + correction_x
        adjusted_delta_y = delta_y + correction_y

        # Traverse mode uses observed angles; coordinate mode derives them from azimuths.
        observed_angle_deg = (
            segment.observed_angle_deg
            if segment.observed_angle_deg is not None
            else _observed_angle_deg(segments, index)
        )
        angular_adjustment_seconds = _finite_or_zero(
            segment.applied_angle_error_seconds
        )
        corrected_angle_deg = (
            (observed_angle_deg + angular_adjustment_seconds / 3600.0) % 360.0
            if observed_angle_deg is not None
            else None
        )

        contribution_status = segment.contribution_status or "baixa"
        row_messages = [
            "Projecoes brutas calculadas por DeltaE=d*sen(Az) e DeltaN=d*cos(Az).",
            "E/W e N/S separam o sinal da projecao como em planilhas manuais.",
        ]
        if correction_x or correction_y:
            row_messages.append(
                "Correcao distribuida pela regra de Bowditch proporcional ao comprimento."
            )
        else:
            row_messages.append(
                "Sem correcao linear aplicada neste segmento porque nao ha residuo de fechamento."
            )
        if angular_adjustment_seconds:
            row_messages.append(
                "Angulo corrigido inclui o ajuste angular informado para o levantamento."
            )

        rows.append(
            PlanimetricTableRow(
                segment=f"{segment.start_vertex}-{segment.end_vertex}",
                station=segment.start_vertex,
                point_initial=segment.start_vertex,
                point_final=segment.end_vertex,
                distance=segment.distance_m,
                distance_m=segment.distance_m,
                observed_angle=(
                    decimal_to_dms(observed_angle_deg)
                    if observed_angle_deg is not None
                    else None
                ),
                observed_angle_deg=observed_angle_deg,
                angular_adjustment=_format_seconds(angular_adjustment_seconds),
                angular_adjustment_seconds=angular_adjustment_seconds,
                corrected_angle=(
                    decimal_to_dms(corrected_angle_deg)
                    if corrected_angle_deg is not None
                    else None
                ),
                corrected_angle_deg=corrected_angle_deg,
                azimuth=segment.azimuth_adjusted_dms
                or segment.azimuth_dms
                or decimal_to_dms(segment.azimuth_deg),
                azimuth_deg=(
                    segment.azimuth_adjusted_deg
                    if segment.azimuth_adjusted_deg is not None
                    else segment.azimuth_deg
                ),
                bearing=segment.bearing,
                east_positive=max(delta_x, 0.0),
                west_negative=min(delta_x, 0.0),
                north_positive=max(delta_y, 0.0),
                south_negative=min(delta_y, 0.0),
                delta_x=delta_x,
                delta_y=delta_y,
                closure_error_x=closure_error_x,
                closure_error_y=closure_error_y,
                correction_x=correction_x,
                correction_y=correction_y,
                adjusted_x=adjusted_delta_x,
                adjusted_y=adjusted_delta_y,
                adjusted_delta_x=adjusted_delta_x,
                adjusted_delta_y=adjusted_delta_y,
                raw_start_x=start.x,
                raw_start_y=start.y,
                raw_end_x=end.x,
                raw_end_y=end.y,
                adjusted_start_x=_coord_x(adjusted_start),
                adjusted_start_y=_coord_y(adjusted_start),
                adjusted_coordinate_x=_coord_x(adjusted_end),
                adjusted_coordinate_y=_coord_y(adjusted_end),
                accumulated_x=_coord_x(adjusted_end),
                accumulated_y=_coord_y(adjusted_end),
                correction_applied=math.hypot(correction_x, correction_y),
                correction_applied_label=(
                    f"Cx={correction_x:.6f} m; Cy={correction_y:.6f} m"
                ),
                error_contribution_percent=_finite_or_zero(
                    segment.contribution_percent
                ),
                status=contribution_status,
                visual_status=_status_severity(contribution_status),
                messages=row_messages,
                observation=segment.observation,
            )
        )

    first = survey_points[0] if survey_points else None
    last = survey_points[-1] if survey_points else None
    final_adjusted = adjusted_points[-1] if adjusted_points else None
    observations = [
        *[str(message) for message in adjustment_summary.get("messages", [])],
        "Tabela gerada com separacao entre valores brutos, corrigidos, ajustados e acumulados.",
    ]

    summary = PlanimetricCalculationSummary(
        perimeter=perimeter_m,
        area=area_m2,
        closure_error_x=closure_error_x,
        closure_error_y=closure_error_y,
        linear_error=_finite_or_zero(adjustment_summary.get("linear_closure_error_m")),
        angular_error_seconds=adjustment_summary.get("angular_closure_error_seconds")
        or adjustment_summary.get("measured_angular_error_seconds")
        or adjustment_summary.get("applied_angular_error_seconds"),
        tolerance=adjustment_summary.get("tolerance_m"),
        tolerance_usage_percent=adjustment_summary.get("tolerance_usage_percent"),
        status=str(adjustment_summary.get("status", "nao_informado")),
        status_label=str(adjustment_summary.get("status_label", "nao informado")),
        adjustment_method=str(
            adjustment_summary.get("adjustment_method", "bowditch_linear_proporcional")
        ),
        correction_sum_x=_finite_or_zero(adjustment_summary.get("correction_sum_e_m")),
        correction_sum_y=_finite_or_zero(adjustment_summary.get("correction_sum_n_m")),
        initial_coordinate_x=first.x if first else None,
        initial_coordinate_y=first.y if first else None,
        final_adjusted_coordinate_x=(
            _coord_x(final_adjusted) if final_adjusted else None
        ),
        final_adjusted_coordinate_y=(
            _coord_y(final_adjusted) if final_adjusted else None
        ),
        final_raw_coordinate_x=last.x if last else None,
        final_raw_coordinate_y=last.y if last else None,
        observations=observations,
    )

    return PlanimetricCalculationTable(
        segments=rows,
        summary=summary,
        formulas=PLANIMETRIC_FORMULAS,
    )
