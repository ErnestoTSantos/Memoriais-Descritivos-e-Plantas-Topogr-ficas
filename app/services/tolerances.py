from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from app.models.schemas import CoordinatePoint, IrradiationObservation, SegmentInfo

SECONDS_PER_DEGREE = 3600.0
SECONDS_PER_MINUTE = 60.0

GLOBAL_STATUS_INSIDE = "dentro_da_tolerancia"
GLOBAL_STATUS_NEAR = "proximo_do_limite"
GLOBAL_STATUS_OUTSIDE = "fora_da_tolerancia"
GLOBAL_STATUS_UNDEFINED = "nao_informado"


@dataclass(frozen=True)
class EquipmentErrorConfig:
    """Instrument error configuration used as a global survey tolerance.

    The equipment tolerance is not applied as an isolated pass/fail limit for
    each segment.  Segment and point values below are individual contributions
    to one accumulated error budget, while the final validation is based on the
    global closure/propagated error.
    """

    linear_error_m: float | None = None
    angular_error_seconds: float | None = None
    distance_precision_m: float | None = None
    angular_precision_seconds: float | None = None
    closure_tolerance_m: float | None = None
    angle_error_limit_seconds: float | None = None
    measured_angular_error_seconds: float | None = None

    @property
    def global_linear_tolerance_m(self) -> float:
        return first_positive(self.linear_error_m, self.closure_tolerance_m, 0.05)

    @property
    def per_distance_precision_m(self) -> float:
        return first_positive(self.distance_precision_m, 0.0)

    @property
    def effective_angular_precision_seconds(self) -> float:
        return first_positive(
            self.angular_precision_seconds,
            self.angular_error_seconds,
            self.angle_error_limit_seconds,
            0.0,
        )

    @property
    def angular_precision_radians(self) -> float:
        return math.radians(
            self.effective_angular_precision_seconds / SECONDS_PER_DEGREE
        )


def first_positive(*values: float | None) -> float:
    for value in values:
        if value is not None and math.isfinite(float(value)) and float(value) > 0.0:
            return float(value)
    return 0.0


def angular_value_to_seconds(
    value: float | None, unit: str | None = None
) -> float | None:
    if value is None:
        return None

    numeric = float(value)
    normalized_unit = (unit or "seconds").strip().lower()
    if normalized_unit in {"degree", "degrees", "grau", "graus", "deg"}:
        return numeric * SECONDS_PER_DEGREE
    if normalized_unit in {"minute", "minutes", "minuto", "minutos", "min"}:
        return numeric * SECONDS_PER_MINUTE
    return numeric


def classify_global_status(error_m: float, tolerance_m: float) -> dict[str, Any]:
    if tolerance_m <= 0.0 or not math.isfinite(tolerance_m):
        return {
            "status": GLOBAL_STATUS_UNDEFINED,
            "label": "tolerancia nao informada",
            "severity": "neutral",
            "usage_percent": None,
        }

    usage_percent = (error_m / tolerance_m) * 100.0 if tolerance_m else 0.0
    if error_m <= tolerance_m * 0.80:
        status = GLOBAL_STATUS_INSIDE
        label = "dentro da tolerancia"
        severity = "success"
    elif error_m <= tolerance_m:
        status = GLOBAL_STATUS_NEAR
        label = "proximo do limite"
        severity = "warning"
    else:
        status = GLOBAL_STATUS_OUTSIDE
        label = "fora da tolerancia"
        severity = "danger"

    return {
        "status": status,
        "label": label,
        "severity": severity,
        "usage_percent": usage_percent,
    }


def classify_contribution(percent: float) -> str:
    if percent <= 20.0:
        return "baixa"
    if percent <= 50.0:
        return "moderada"
    return "alta"


def _severity_rank(status: str) -> int:
    return {
        GLOBAL_STATUS_UNDEFINED: 0,
        GLOBAL_STATUS_INSIDE: 1,
        GLOBAL_STATUS_NEAR: 2,
        GLOBAL_STATUS_OUTSIDE: 3,
    }.get(status, 0)


def _worst_status(*items: dict[str, Any]) -> dict[str, Any]:
    return max(items, key=lambda item: _severity_rank(str(item.get("status", ""))))


def _segment_delta(start: CoordinatePoint, end: CoordinatePoint) -> tuple[float, float]:
    return end.x - start.x, end.y - start.y


def angular_closure_error_seconds(segments: list[SegmentInfo]) -> float | None:
    """Return geometric angular closure error in seconds when a ring exists.

    This is a consistency check from computed azimuths, not a substitute for
    observed angle adjustment.  With no measured interior angles, the function
    can only detect whether the segment azimuth sequence closes to 360 degrees.
    """

    if len(segments) < 3:
        return None

    total_turn = 0.0
    for index, segment in enumerate(segments):
        next_segment = segments[(index + 1) % len(segments)]
        turn = (next_segment.azimuth_deg - segment.azimuth_deg + 180.0) % 360.0 - 180.0
        total_turn += turn

    return abs(abs(total_turn) - 360.0) * SECONDS_PER_DEGREE


def _area_uncertainty(perimeter_m: float, tolerance_m: float) -> float:
    # First-order approximation: shifting the boundary by a small radial
    # tolerance changes area roughly by perimeter * displacement.
    if perimeter_m <= 0.0 or tolerance_m <= 0.0:
        return 0.0
    return perimeter_m * tolerance_m


def build_linear_adjustment_diagnostics(
    survey_points: list[CoordinatePoint],
    segments: list[SegmentInfo],
    config: EquipmentErrorConfig,
    closure_dx_m: float,
    closure_dy_m: float,
    closure_error_m: float,
    perimeter_m: float,
    area_m2: float,
    residual_closure: bool,
) -> tuple[list[CoordinatePoint], list[SegmentInfo], dict[str, Any]]:
    """Distribute closing error proportionally by segment length.

    The method is the linear Bowditch/compass-rule adjustment:

    correction_E_i = -closure_E * (length_i / total_length)
    correction_N_i = -closure_N * (length_i / total_length)

    The sum of all corrections cancels the closing vector, but no segment is
    independently approved or rejected; each segment only receives a share of
    the global adjustment.
    """

    tolerance_m = config.global_linear_tolerance_m
    distance_precision_m = config.per_distance_precision_m
    segment_lengths = [max(0.0, segment.distance_m) for segment in segments]
    adjustment_length = sum(segment_lengths)
    propagated_linear_error_m = (
        math.sqrt(len(segments)) * distance_precision_m
        if distance_precision_m > 0.0
        else 0.0
    )
    accumulated_error_m = math.hypot(closure_error_m, propagated_linear_error_m)
    global_status = classify_global_status(accumulated_error_m, tolerance_m)
    angular_closure_seconds = (
        None if residual_closure else angular_closure_error_seconds(segments)
    )
    angular_tolerance_seconds = config.effective_angular_precision_seconds
    measured_angular_error_seconds = abs(config.measured_angular_error_seconds or 0.0)
    angular_error_seconds = max(
        angular_closure_seconds or 0.0, measured_angular_error_seconds
    )
    angular_status = (
        classify_global_status(angular_error_seconds, angular_tolerance_seconds)
        if angular_tolerance_seconds > 0.0
        and (
            angular_closure_seconds is not None or measured_angular_error_seconds > 0.0
        )
        else {
            "status": GLOBAL_STATUS_UNDEFINED,
            "label": "fechamento angular nao aplicavel",
            "severity": "neutral",
            "usage_percent": None,
        }
    )
    overall = _worst_status(global_status, angular_status)

    adjusted_points: list[CoordinatePoint] = []
    if survey_points:
        first = survey_points[0]
        adjusted_points.append(
            first.model_copy(
                update={
                    "adjusted_x": first.x,
                    "adjusted_y": first.y,
                    "correction_e_m": 0.0,
                    "correction_n_m": 0.0,
                    "estimated_error_m": 0.0,
                    "contribution_percent": 0.0,
                    "contribution_status": "baixa",
                    "observation": "Ponto inicial da distribuicao do fechamento.",
                }
            )
        )

    adjusted_segments: list[SegmentInfo] = []
    current_adjusted_x = survey_points[0].x if survey_points else 0.0
    current_adjusted_y = survey_points[0].y if survey_points else 0.0
    correction_sum_e = 0.0
    correction_sum_n = 0.0

    for index, segment in enumerate(segments):
        start = survey_points[index]
        end = survey_points[index + 1]
        delta_e, delta_n = _segment_delta(start, end)
        share = (
            segment.distance_m / adjustment_length if adjustment_length > 0.0 else 0.0
        )
        correction_e = -closure_dx_m * share if residual_closure else 0.0
        correction_n = -closure_dy_m * share if residual_closure else 0.0
        adjusted_delta_e = delta_e + correction_e
        adjusted_delta_n = delta_n + correction_n
        current_adjusted_x += adjusted_delta_e
        current_adjusted_y += adjusted_delta_n
        correction_sum_e += correction_e
        correction_sum_n += correction_n

        closure_influence = closure_error_m * share
        propagated_share = propagated_linear_error_m * share
        estimated_error = math.hypot(closure_influence, propagated_share)
        contribution_percent = share * 100.0 if adjustment_length > 0.0 else 0.0
        contribution_status = classify_contribution(contribution_percent)

        adjusted_segments.append(
            segment.model_copy(
                update={
                    "delta_e_m": delta_e,
                    "delta_n_m": delta_n,
                    "correction_e_m": correction_e,
                    "correction_n_m": correction_n,
                    "adjusted_delta_e_m": adjusted_delta_e,
                    "adjusted_delta_n_m": adjusted_delta_n,
                    "adjusted_distance_m": math.hypot(
                        adjusted_delta_e, adjusted_delta_n
                    ),
                    "estimated_error_m": estimated_error,
                    "propagated_error_m": propagated_share,
                    "linear_error_component_m": propagated_share,
                    "closure_influence_m": closure_influence,
                    "closure_participation_percent": contribution_percent,
                    "contribution_percent": contribution_percent,
                    "contribution_status": contribution_status,
                    "observation": (
                        "Esta medida contribui para o erro total do levantamento. "
                        "A correcao apresentada faz parte da distribuicao do erro "
                        "de fechamento considerando a tolerancia do equipamento."
                    ),
                }
            )
        )

        point_correction_e = current_adjusted_x - end.x
        point_correction_n = current_adjusted_y - end.y
        adjusted_points.append(
            end.model_copy(
                update={
                    "adjusted_x": current_adjusted_x,
                    "adjusted_y": current_adjusted_y,
                    "correction_e_m": point_correction_e,
                    "correction_n_m": point_correction_n,
                    "estimated_error_m": estimated_error,
                    "linear_error_component_m": propagated_share,
                    "contribution_percent": contribution_percent,
                    "contribution_status": contribution_status,
                    "observation": (
                        "Coordenada ajustada pela soma acumulada das correcoes "
                        "distribuidas nos segmentos anteriores."
                    ),
                }
            )
        )

    summary = {
        "mode": "ponto_a_ponto",
        "status": overall["status"],
        "status_label": overall["label"],
        "severity": overall["severity"],
        "accumulated_error_m": accumulated_error_m,
        "tolerance_m": tolerance_m,
        "tolerance_usage_percent": global_status["usage_percent"],
        "closure_error_m": closure_error_m,
        "linear_closure_error_m": closure_error_m,
        "closure_dx_m": closure_dx_m,
        "closure_dy_m": closure_dy_m,
        "angular_closure_error_seconds": angular_closure_seconds,
        "measured_angular_error_seconds": measured_angular_error_seconds or None,
        "angular_tolerance_seconds": angular_tolerance_seconds or None,
        "angular_status": angular_status["status"],
        "angular_status_label": angular_status["label"],
        "angular_usage_percent": angular_status["usage_percent"],
        "propagated_linear_error_m": propagated_linear_error_m,
        "propagated_angular_error_m": 0.0,
        "perimeter_error_ratio": (
            closure_error_m / perimeter_m if perimeter_m > 0.0 else 0.0
        ),
        "relative_precision_ratio": (
            perimeter_m / closure_error_m if closure_error_m > 0.0 else None
        ),
        "area_uncertainty_m2": _area_uncertainty(perimeter_m, tolerance_m),
        "adjustment_method": "bowditch_linear_proporcional",
        "correction_sum_e_m": correction_sum_e,
        "correction_sum_n_m": correction_sum_n,
        "residual_closure": residual_closure,
        "equipment": {
            "linear_error_m": config.linear_error_m,
            "angular_error_seconds": config.angular_error_seconds,
            "distance_precision_m": config.distance_precision_m,
            "angular_precision_seconds": config.angular_precision_seconds,
            "closure_tolerance_m": config.closure_tolerance_m,
            "angle_error_limit_seconds": config.angle_error_limit_seconds,
            "measured_angular_error_seconds": config.measured_angular_error_seconds,
        },
        "messages": [
            "A tolerancia do equipamento e avaliada no fechamento global, nao como limite isolado por segmento.",
            "As correcoes foram distribuidas proporcionalmente ao comprimento de cada medida.",
        ],
    }

    return adjusted_points, adjusted_segments, summary


def _resolve_station(
    observation: IrradiationObservation,
    default_station_x: float | None,
    default_station_y: float | None,
) -> tuple[float | None, float | None]:
    station_x = (
        observation.station_x
        if observation.station_x is not None
        else default_station_x
    )
    station_y = (
        observation.station_y
        if observation.station_y is not None
        else default_station_y
    )
    return station_x, station_y


def enrich_irradiation_diagnostics(
    observations: list[IrradiationObservation],
    adjusted_points: list[CoordinatePoint],
    config: EquipmentErrorConfig,
    default_station_x: float | None,
    default_station_y: float | None,
    applied_angle_error_seconds: float | None,
    summary: dict[str, Any],
) -> tuple[list[CoordinatePoint], dict[str, Any]]:
    """Add irradiation propagation terms to points and global summary.

    For each observation:

    DeltaE = d * sin(Az)
    DeltaN = d * cos(Az)

    Propagation uses the first-order partial derivatives:
    dE/dd = sin(Az), dN/dd = cos(Az),
    dE/dAz = d * cos(Az), dN/dAz = -d * sin(Az), with Az in radians.

    Therefore the angular displacement grows linearly with distance; a small
    angular precision in seconds can dominate the coordinate uncertainty for
    farther points.
    """

    distance_precision_m = config.per_distance_precision_m
    angular_precision_seconds = config.effective_angular_precision_seconds
    angular_precision_rad = config.angular_precision_radians
    propagated_items: list[dict[str, Any]] = []
    propagated_square_sum = 0.0
    angular_square_sum = 0.0

    for observation in observations:
        corrected_azimuth = (
            observation.azimuth_deg + ((applied_angle_error_seconds or 0.0) / 3600.0)
        ) % 360.0
        azimuth_rad = math.radians(corrected_azimuth)
        distance_m = float(observation.distance_m)

        linear_e = abs(distance_precision_m * math.sin(azimuth_rad))
        linear_n = abs(distance_precision_m * math.cos(azimuth_rad))
        angular_e = abs(distance_m * angular_precision_rad * math.cos(azimuth_rad))
        angular_n = abs(distance_m * angular_precision_rad * math.sin(azimuth_rad))
        linear_component = math.hypot(linear_e, linear_n)
        angular_component = math.hypot(angular_e, angular_n)
        estimated_error = math.hypot(linear_component, angular_component)
        propagated_square_sum += estimated_error**2
        angular_square_sum += angular_component**2
        station_x, station_y = _resolve_station(
            observation, default_station_x, default_station_y
        )
        propagated_items.append(
            {
                "vertex": observation.vertex,
                "station_x": station_x,
                "station_y": station_y,
                "distance_m": distance_m,
                "azimuth_deg": observation.azimuth_deg,
                "corrected_azimuth_deg": corrected_azimuth,
                "linear_error_component_m": linear_component,
                "angular_error_component_m": angular_component,
                "estimated_error_m": estimated_error,
            }
        )

    total_propagated_error_m = math.sqrt(propagated_square_sum)
    total_angular_error_m = math.sqrt(angular_square_sum)
    point_by_vertex = {item["vertex"]: item for item in propagated_items}
    enriched_points: list[CoordinatePoint] = []

    for point in adjusted_points:
        item = point_by_vertex.get(point.vertex)
        if not item:
            enriched_points.append(point)
            continue

        contribution_percent = (
            (item["estimated_error_m"] ** 2 / propagated_square_sum) * 100.0
            if propagated_square_sum > 0.0
            else 0.0
        )
        contribution_status = classify_contribution(contribution_percent)
        enriched_points.append(
            point.model_copy(
                update={
                    "estimated_error_m": item["estimated_error_m"],
                    "linear_error_component_m": item["linear_error_component_m"],
                    "angular_error_component_m": item["angular_error_component_m"],
                    "contribution_percent": contribution_percent,
                    "contribution_status": contribution_status,
                    "observation": (
                        "Pequenos erros angulares podem gerar deslocamentos maiores "
                        "conforme a distancia observada aumenta."
                    ),
                }
            )
        )

    accumulated_error_m = math.hypot(
        float(summary.get("closure_error_m") or 0.0),
        total_propagated_error_m,
    )
    tolerance_m = float(summary.get("tolerance_m") or config.global_linear_tolerance_m)
    linear_global_status = classify_global_status(accumulated_error_m, tolerance_m)
    applied_angle = abs(applied_angle_error_seconds or 0.0)
    angular_status = (
        classify_global_status(applied_angle, angular_precision_seconds)
        if angular_precision_seconds > 0.0
        else {
            "status": GLOBAL_STATUS_UNDEFINED,
            "label": "precisao angular nao informada",
            "severity": "neutral",
            "usage_percent": None,
        }
    )
    overall = _worst_status(linear_global_status, angular_status)

    enriched_summary = {
        **summary,
        "mode": "irradiacao",
        "status": overall["status"],
        "status_label": overall["label"],
        "severity": overall["severity"],
        "accumulated_error_m": accumulated_error_m,
        "tolerance_usage_percent": linear_global_status["usage_percent"],
        "angular_status": angular_status["status"],
        "angular_status_label": angular_status["label"],
        "angular_usage_percent": angular_status["usage_percent"],
        "applied_angular_error_seconds": applied_angle,
        "propagated_linear_error_m": total_propagated_error_m,
        "propagated_angular_error_m": total_angular_error_m,
        "irradiation_points": propagated_items,
        "messages": [
            *summary.get("messages", []),
            "Na irradiacao, a influencia angular cresce com a distancia entre estacao e ponto.",
            "O erro acumulado considera o conjunto dos pontos irradiados.",
        ],
    }

    return enriched_points, enriched_summary
