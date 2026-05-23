from __future__ import annotations

from pydantic import BaseModel


class CoordinatePoint(BaseModel):
    vertex: str
    x: float
    y: float
    adjusted_x: float | None = None
    adjusted_y: float | None = None
    correction_e_m: float = 0.0
    correction_n_m: float = 0.0
    estimated_error_m: float = 0.0
    linear_error_component_m: float = 0.0
    angular_error_component_m: float = 0.0
    contribution_percent: float = 0.0
    contribution_status: str = "baixa"
    observation: str = ""


class IrradiationObservation(BaseModel):
    vertex: str
    azimuth_deg: float
    distance_m: float
    station_x: float | None = None
    station_y: float | None = None
    station_name: str | None = None


class IrradiationTableRow(BaseModel):
    """One row of the irradiation calculation table (per observed point)."""

    station_name: str
    station_x: float
    station_y: float
    vertex: str
    distance_m: float
    azimuth_deg: float
    azimuth_dms: str
    delta_x: float
    delta_y: float
    x: float
    y: float


class IrradiationTable(BaseModel):
    """Complete irradiation calculation table with all intermediate values."""

    rows: list[IrradiationTableRow]


class SegmentInfo(BaseModel):
    start_vertex: str
    end_vertex: str
    distance_m: float
    azimuth_deg: float
    azimuth_dms: str
    azimuth_adjusted_deg: float | None = None
    azimuth_adjusted_dms: str | None = None
    applied_angle_error_seconds: float = 0.0
    observed_angle_deg: float | None = None
    bearing: str
    delta_e_m: float = 0.0
    delta_n_m: float = 0.0
    correction_e_m: float = 0.0
    correction_n_m: float = 0.0
    adjusted_delta_e_m: float = 0.0
    adjusted_delta_n_m: float = 0.0
    adjusted_distance_m: float | None = None
    estimated_error_m: float = 0.0
    propagated_error_m: float = 0.0
    linear_error_component_m: float = 0.0
    angular_error_component_m: float = 0.0
    closure_influence_m: float = 0.0
    closure_participation_percent: float = 0.0
    contribution_percent: float = 0.0
    contribution_status: str = "baixa"
    observation: str = ""


class PlanimetricTableRow(BaseModel):
    """DTO for one audited row of the manual planimetric calculation table."""

    segment: str
    station: str
    point_initial: str
    point_final: str

    distance: float
    distance_m: float

    observed_angle: str | None = None
    observed_angle_deg: float | None = None
    angular_adjustment: str
    angular_adjustment_seconds: float
    corrected_angle: str | None = None
    corrected_angle_deg: float | None = None

    azimuth: str
    azimuth_deg: float
    bearing: str

    east_positive: float
    west_negative: float
    north_positive: float
    south_negative: float
    delta_x: float
    delta_y: float

    closure_error_x: float
    closure_error_y: float
    correction_x: float
    correction_y: float
    adjusted_x: float
    adjusted_y: float
    adjusted_delta_x: float
    adjusted_delta_y: float

    raw_start_x: float
    raw_start_y: float
    raw_end_x: float
    raw_end_y: float
    adjusted_start_x: float
    adjusted_start_y: float
    adjusted_coordinate_x: float
    adjusted_coordinate_y: float
    accumulated_x: float
    accumulated_y: float

    correction_applied: float
    correction_applied_label: str
    error_contribution_percent: float
    status: str
    visual_status: str
    messages: list[str]
    observation: str


class PlanimetricCalculationSummary(BaseModel):
    """Global result of the planimetric table and closing adjustment."""

    perimeter: float
    area: float
    closure_error_x: float
    closure_error_y: float
    linear_error: float
    angular_error_seconds: float | None = None
    tolerance: float | None = None
    tolerance_usage_percent: float | None = None
    status: str
    status_label: str
    adjustment_method: str
    correction_sum_x: float
    correction_sum_y: float
    initial_coordinate_x: float | None = None
    initial_coordinate_y: float | None = None
    final_adjusted_coordinate_x: float | None = None
    final_adjusted_coordinate_y: float | None = None
    final_raw_coordinate_x: float | None = None
    final_raw_coordinate_y: float | None = None
    observations: list[str]


class PlanimetricCalculationTable(BaseModel):
    """Complete serializable planimetric calculation table."""

    segments: list[PlanimetricTableRow]
    summary: PlanimetricCalculationSummary
    formulas: dict[str, str]


class TraverseObservation(BaseModel):
    """One row of traverse field data (caminhamento)."""

    station: str
    sighted_point: str
    distance_m: float
    observed_angle_deg: float
    observed_angle_dms: str | None = None


class TraverseAngularSummary(BaseModel):
    """Angular closure summary for a planimetric traverse."""

    n_sides: int
    angular_misclosure_seconds: float
    allowed_error_seconds: float | None
    correction_per_side_seconds: float
    status: str   # "ok" | "warning" | "nao_informado"
    status_label: str
