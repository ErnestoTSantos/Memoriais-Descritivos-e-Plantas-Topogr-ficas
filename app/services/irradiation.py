from __future__ import annotations

import math

from app.models.schemas import CoordinatePoint, IrradiationObservation


def irradiation_to_points(
    observations: list[IrradiationObservation],
    origin_x: float | None = None,
    origin_y: float | None = None,
    angle_error_seconds: float = 0.0,
) -> list[CoordinatePoint]:
    if len(observations) < 3:
        raise ValueError("Informe ao menos 3 observacoes de irradiacao para formar o poligono.")

    has_explicit_station = any(obs.station_x is not None or obs.station_y is not None for obs in observations)
    if has_explicit_station:
        ordered_observations = observations
    else:
        ordered_observations = sorted(observations, key=lambda obs: obs.azimuth_deg % 360)

    points: list[CoordinatePoint] = []
    for obs in ordered_observations:
        if obs.distance_m <= 0:
            raise ValueError("A distancia da irradiacao deve ser maior que zero.")

        station_x = obs.station_x if obs.station_x is not None else origin_x
        station_y = obs.station_y if obs.station_y is not None else origin_y
        if station_x is None or station_y is None:
            raise ValueError(
                "Para irradiacao informe X e Y da estacao no formulario ou em cada observacao."
            )

        corrected_azimuth_deg = (obs.azimuth_deg + (angle_error_seconds / 3600.0)) % 360.0
        azimuth_rad = math.radians(corrected_azimuth_deg)
        x = station_x + obs.distance_m * math.sin(azimuth_rad)
        y = station_y + obs.distance_m * math.cos(azimuth_rad)
        points.append(CoordinatePoint(vertex=obs.vertex, x=x, y=y))

    return points
