from __future__ import annotations

from pydantic import BaseModel


class CoordinatePoint(BaseModel):
    vertex: str
    x: float
    y: float


class IrradiationObservation(BaseModel):
    vertex: str
    azimuth_deg: float
    distance_m: float
    station_x: float | None = None
    station_y: float | None = None


class SegmentInfo(BaseModel):
    start_vertex: str
    end_vertex: str
    distance_m: float
    azimuth_deg: float
    azimuth_dms: str
    azimuth_adjusted_deg: float | None = None
    azimuth_adjusted_dms: str | None = None
    applied_angle_error_seconds: float = 0.0
    bearing: str
