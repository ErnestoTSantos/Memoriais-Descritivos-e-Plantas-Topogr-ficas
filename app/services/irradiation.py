from __future__ import annotations

import math

from app.models.schemas import (
    CoordinatePoint,
    IrradiationObservation,
    IrradiationTable,
    IrradiationTableRow,
)
from app.services.angles import decimal_to_dms


def _finite_float(value: float | None, field_name: str, vertex: str) -> float | None:
    if value is None:
        return None
    numeric = float(value)
    if not math.isfinite(numeric):
        raise ValueError(
            f"Vertice '{vertex}': {field_name} deve ser numerico e finito."
        )
    return numeric


def compute_irradiation(
    observations: list[IrradiationObservation],
    origin_x: float | None = None,
    origin_y: float | None = None,
    angle_error_seconds: float = 0.0,
    stations: dict[str, tuple[float, float]] | None = None,
) -> tuple[list[CoordinatePoint], IrradiationTable]:
    """Compute irradiation points and the full intermediate calculation table.

    Returns a tuple of (points, table) where *points* preserves the field/input
    order. Polygon ordering is a surveying decision and must not be inferred by
    the irradiation conversion layer.

    Parameters
    ----------
    observations:
        List of irradiation observations, each with vertex, azimuth_deg,
        distance_m, and optionally station_name / station_x / station_y.
    origin_x, origin_y:
        Default station coordinates for single-station backward compat.
    angle_error_seconds:
        Equipment angular error in arc-seconds applied to all azimuths.
    stations:
        Named stations dict for multi-station irradiation.  Keys are station
        names; values are (x, y) tuples.  When provided, each observation is
        resolved against this dict by its station_name field.
    """
    if len(observations) < 3:
        raise ValueError(
            "Informe ao menos 3 observacoes de irradiacao para formar o poligono."
        )

    if not math.isfinite(float(angle_error_seconds)):
        raise ValueError("O erro angular deve ser numerico e finito.")

    origin_x = _finite_float(origin_x, "X da estacao", "origem")
    origin_y = _finite_float(origin_y, "Y da estacao", "origem")

    for obs in observations:
        x_set = obs.station_x is not None
        y_set = obs.station_y is not None
        if x_set != y_set:
            raise ValueError(
                f"Vertice '{obs.vertex}': estacao parcialmente definida — "
                "informe station_x E station_y juntos, ou deixe ambos em branco."
            )

    ordered_observations = observations

    points: list[CoordinatePoint] = []
    table_rows: list[IrradiationTableRow] = []

    for obs in ordered_observations:
        distance_m = _finite_float(obs.distance_m, "distancia", obs.vertex)
        azimuth_deg = _finite_float(obs.azimuth_deg, "azimute", obs.vertex)
        obs_station_x = _finite_float(obs.station_x, "X da estacao", obs.vertex)
        obs_station_y = _finite_float(obs.station_y, "Y da estacao", obs.vertex)

        if distance_m is None or distance_m <= 0:
            raise ValueError("A distancia da irradiacao deve ser maior que zero.")

        # Station resolution priority:
        # 1. Named stations dict (multi-station): match by obs.station_name.
        # 2. Per-observation station_x/y (legacy inline coordinates).
        # 3. Default origin_x/y (single-station fallback).
        station_x: float | None = None
        station_y: float | None = None

        if stations:
            sname = obs.station_name or ""
            if sname and sname in stations:
                station_x, station_y = stations[sname]
            elif sname and sname not in stations:
                raise ValueError(
                    f"Vertice '{obs.vertex}': estacao '{sname}' nao encontrada. "
                    "Cadastre a estacao antes de usar."
                )
            elif not sname and len(stations) == 1:
                station_x, station_y = next(iter(stations.values()))
            else:
                raise ValueError(
                    f"Vertice '{obs.vertex}': informe o nome da estacao "
                    "(mais de uma estacao cadastrada)."
                )
        elif obs_station_x is not None:
            station_x = obs_station_x
            station_y = obs_station_y
        else:
            station_x = origin_x
            station_y = origin_y

        if station_x is None or station_y is None:
            raise ValueError(
                f"Vertice '{obs.vertex}': coordenadas da estacao nao disponiveis. "
                "informe X e Y da estacao no formulario."
            )

        corrected_azimuth_deg = (
            azimuth_deg + (float(angle_error_seconds) / 3600.0)
        ) % 360.0
        azimuth_rad = math.radians(corrected_azimuth_deg)

        # ΔX = d × sen(Az)    ΔY = d × cos(Az)
        delta_x = distance_m * math.sin(azimuth_rad)
        delta_y = distance_m * math.cos(azimuth_rad)
        x = station_x + delta_x
        y = station_y + delta_y

        station_label = (
            obs.station_name
            if obs.station_name
            else f"({station_x:.3f}, {station_y:.3f})"
        )

        points.append(CoordinatePoint(vertex=obs.vertex, x=x, y=y))
        table_rows.append(
            IrradiationTableRow(
                station_name=station_label,
                station_x=station_x,
                station_y=station_y,
                vertex=obs.vertex,
                distance_m=distance_m,
                azimuth_deg=corrected_azimuth_deg,
                azimuth_dms=decimal_to_dms(corrected_azimuth_deg),
                delta_x=delta_x,
                delta_y=delta_y,
                x=x,
                y=y,
            )
        )

    return points, IrradiationTable(rows=table_rows)


def irradiation_to_points(
    observations: list[IrradiationObservation],
    origin_x: float | None = None,
    origin_y: float | None = None,
    angle_error_seconds: float = 0.0,
) -> list[CoordinatePoint]:
    """Backward-compatible wrapper — returns only the computed points.

    Use compute_irradiation() when intermediate table values are also needed.
    """
    points, _ = compute_irradiation(
        observations, origin_x, origin_y, angle_error_seconds
    )
    return points
