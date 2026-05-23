from __future__ import annotations

import itertools
import math
from dataclasses import dataclass

from app.models.schemas import CoordinatePoint
from app.services.angles import decimal_to_dms
from app.services.geometry import polygon_area


SECONDS_PER_DEGREE = 3600.0


@dataclass(frozen=True)
class PlanimetryLeg:
    start_vertex: str
    end_vertex: str
    distance_m: float
    adjusted_angle_deg: float


@dataclass(frozen=True)
class PlanimetrySegment:
    start_vertex: str
    end_vertex: str
    distance_m: float
    adjusted_angle_deg: float
    azimuth_deg: float
    azimuth_dms: str
    bearing: str
    reported_delta_e_m: float
    reported_delta_n_m: float
    projection_azimuth_deg: float
    projection_azimuth_dms: str
    delta_e_m: float
    delta_n_m: float
    correction_e_m: float
    correction_n_m: float
    adjusted_delta_e_m: float
    adjusted_delta_n_m: float
    projection_direction_reversed: bool


@dataclass(frozen=True)
class PlanimetryResult:
    segments: list[PlanimetrySegment]
    raw_points: list[CoordinatePoint]
    adjusted_points: list[CoordinatePoint]
    perimeter_m: float
    area_m2: float
    closure_dx_m: float
    closure_dy_m: float
    closure_error_m: float
    reported_closure_dx_m: float
    reported_closure_dy_m: float
    reported_closure_error_m: float
    angular_misclosure_seconds: float
    applied_angle_correction_seconds: float


def _normalize_angle(angle_deg: float) -> float:
    return float(angle_deg) % 360.0


def _signed_angle_delta(a_deg: float, b_deg: float) -> float:
    return (float(a_deg) - float(b_deg) + 180.0) % 360.0 - 180.0


def _finite_positive(value: float, field_name: str) -> float:
    numeric = float(value)
    if not math.isfinite(numeric) or numeric <= 0.0:
        raise ValueError(f"{field_name} deve ser maior que zero e finito.")
    return numeric


def _format_bearing_angle(angle_deg: float) -> str:
    dms = decimal_to_dms(angle_deg)
    deg, rest = dms.split("\u00b0", maxsplit=1)
    return f"{int(deg):02d}\u00b0{rest}"


def azimuth_to_quadrant_bearing(azimuth_deg: float) -> str:
    az = _normalize_angle(azimuth_deg)
    if 0.0 <= az < 90.0:
        return f"{_format_bearing_angle(az)} NE"
    if 90.0 <= az < 180.0:
        return f"{_format_bearing_angle(180.0 - az)} SE"
    if 180.0 <= az < 270.0:
        return f"{_format_bearing_angle(az - 180.0)} SW"
    return f"{_format_bearing_angle(360.0 - az)} NW"


def _delta(distance_m: float, azimuth_deg: float) -> tuple[float, float]:
    radians = math.radians(_normalize_angle(azimuth_deg))
    return distance_m * math.sin(radians), distance_m * math.cos(radians)


def _build_azimuths(
    legs: list[PlanimetryLeg],
    initial_azimuth_deg: float,
    *,
    balance_angular_closure: bool,
) -> tuple[list[float], list[float], float, float]:
    angle_sum = sum(leg.adjusted_angle_deg for leg in legs)
    angular_misclosure_deg = _signed_angle_delta(angle_sum, 360.0)
    correction_deg = (
        -angular_misclosure_deg / len(legs) if balance_angular_closure else 0.0
    )
    balanced_angles = [
        _normalize_angle(leg.adjusted_angle_deg + correction_deg) for leg in legs
    ]

    azimuths = [_normalize_angle(initial_azimuth_deg)]
    for index in range(1, len(legs)):
        azimuths.append(_normalize_angle(azimuths[-1] + balanced_angles[index]))

    return (
        azimuths,
        balanced_angles,
        angular_misclosure_deg * SECONDS_PER_DEGREE,
        correction_deg * SECONDS_PER_DEGREE,
    )


def _choose_projection_azimuths(
    legs: list[PlanimetryLeg],
    azimuths: list[float],
    *,
    minimize_closure: bool,
) -> tuple[list[float], tuple[bool, ...]]:
    if not minimize_closure:
        return azimuths, tuple(False for _ in azimuths)

    best: tuple[float, int, int, tuple[bool, ...], list[float]] | None = None
    for flips in itertools.product((False, True), repeat=len(azimuths)):
        candidate = [
            _normalize_angle(azimuth + (180.0 if flip else 0.0))
            for azimuth, flip in zip(azimuths, flips, strict=True)
        ]
        closure_e = 0.0
        closure_n = 0.0
        for leg, projection_azimuth in zip(legs, candidate, strict=True):
            delta_e, delta_n = _delta(leg.distance_m, projection_azimuth)
            closure_e += delta_e
            closure_n += delta_n

        # Round the metric used in the key so floating point noise does not
        # choose the globally inverted traverse over an equivalent orientation.
        closure_key = round(math.hypot(closure_e, closure_n), 9)
        first_leg_penalty = 1 if flips[0] else 0
        flip_count = sum(1 for flip in flips if flip)
        key = (closure_key, first_leg_penalty, flip_count, flips, candidate)
        if best is None or key < best:
            best = key

    assert best is not None
    return best[4], best[3]


def compute_planimetry_traverse(
    legs: list[PlanimetryLeg],
    *,
    initial_azimuth_deg: float,
    balance_angular_closure: bool = True,
    minimize_projection_closure: bool = True,
) -> PlanimetryResult:
    if len(legs) < 3:
        raise ValueError("Informe ao menos 3 lados para calcular a poligonal.")

    normalized_legs = [
        PlanimetryLeg(
            start_vertex=leg.start_vertex,
            end_vertex=leg.end_vertex,
            distance_m=_finite_positive(leg.distance_m, "distancia"),
            adjusted_angle_deg=_normalize_angle(leg.adjusted_angle_deg),
        )
        for leg in legs
    ]
    perimeter = sum(leg.distance_m for leg in normalized_legs)

    azimuths, balanced_angles, angular_misclosure_s, angle_correction_s = _build_azimuths(
        normalized_legs,
        initial_azimuth_deg,
        balance_angular_closure=balance_angular_closure,
    )
    projection_azimuths, reversed_flags = _choose_projection_azimuths(
        normalized_legs,
        azimuths,
        minimize_closure=minimize_projection_closure,
    )

    reported_closure_e = 0.0
    reported_closure_n = 0.0
    for leg, azimuth in zip(normalized_legs, azimuths, strict=True):
        delta_e, delta_n = _delta(leg.distance_m, azimuth)
        reported_closure_e += delta_e
        reported_closure_n += delta_n

    projection_deltas = [
        _delta(leg.distance_m, projection_azimuth)
        for leg, projection_azimuth in zip(
            normalized_legs, projection_azimuths, strict=True
        )
    ]
    closure_e = sum(delta_e for delta_e, _ in projection_deltas)
    closure_n = sum(delta_n for _, delta_n in projection_deltas)

    raw_points = [
        CoordinatePoint(vertex=normalized_legs[0].start_vertex, x=0.0, y=0.0)
    ]
    adjusted_points = [
        CoordinatePoint(vertex=normalized_legs[0].start_vertex, x=0.0, y=0.0)
    ]
    current_raw_e = 0.0
    current_raw_n = 0.0
    current_adjusted_e = 0.0
    current_adjusted_n = 0.0
    segments: list[PlanimetrySegment] = []

    for leg, angle, azimuth, projection_azimuth, reversed_flag, (
        delta_e,
        delta_n,
    ) in zip(
        normalized_legs,
        balanced_angles,
        azimuths,
        projection_azimuths,
        reversed_flags,
        projection_deltas,
        strict=True,
    ):
        reported_delta_e, reported_delta_n = _delta(leg.distance_m, azimuth)
        share = leg.distance_m / perimeter if perimeter > 0.0 else 0.0
        correction_e = -closure_e * share
        correction_n = -closure_n * share
        adjusted_delta_e = delta_e + correction_e
        adjusted_delta_n = delta_n + correction_n

        current_raw_e += delta_e
        current_raw_n += delta_n
        current_adjusted_e += adjusted_delta_e
        current_adjusted_n += adjusted_delta_n
        raw_points.append(
            CoordinatePoint(vertex=leg.end_vertex, x=current_raw_e, y=current_raw_n)
        )
        adjusted_points.append(
            CoordinatePoint(
                vertex=leg.end_vertex,
                x=current_adjusted_e,
                y=current_adjusted_n,
            )
        )

        segments.append(
            PlanimetrySegment(
                start_vertex=leg.start_vertex,
                end_vertex=leg.end_vertex,
                distance_m=leg.distance_m,
                adjusted_angle_deg=angle,
                azimuth_deg=azimuth,
                azimuth_dms=decimal_to_dms(azimuth),
                bearing=azimuth_to_quadrant_bearing(azimuth),
                reported_delta_e_m=reported_delta_e,
                reported_delta_n_m=reported_delta_n,
                projection_azimuth_deg=projection_azimuth,
                projection_azimuth_dms=decimal_to_dms(projection_azimuth),
                delta_e_m=delta_e,
                delta_n_m=delta_n,
                correction_e_m=correction_e,
                correction_n_m=correction_n,
                adjusted_delta_e_m=adjusted_delta_e,
                adjusted_delta_n_m=adjusted_delta_n,
                projection_direction_reversed=reversed_flag,
            )
        )

    return PlanimetryResult(
        segments=segments,
        raw_points=raw_points,
        adjusted_points=adjusted_points,
        perimeter_m=perimeter,
        area_m2=polygon_area(adjusted_points),
        closure_dx_m=closure_e,
        closure_dy_m=closure_n,
        closure_error_m=math.hypot(closure_e, closure_n),
        reported_closure_dx_m=reported_closure_e,
        reported_closure_dy_m=reported_closure_n,
        reported_closure_error_m=math.hypot(
            reported_closure_e, reported_closure_n
        ),
        angular_misclosure_seconds=angular_misclosure_s,
        applied_angle_correction_seconds=angle_correction_s,
    )
