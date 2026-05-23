"""Tests for the planimetric traverse mode (angle + distance input)."""
from __future__ import annotations

import math

import pytest

from app.models.schemas import TraverseObservation
from app.services.planimetry import PlanimetryLeg, compute_planimetry_traverse
from app.services.processing import ProjectData, Station, build_project_data, process_traverse



def _project(**kwargs) -> ProjectData:
    defaults = dict(
        property_name="Teste",
        owner_name="Dono",
        municipality="Municipio",
        state="SP",
        datum="SIRGAS2000",
        coordinate_system="UTM",
        measurement_mode="planimetrico",
        stations=[],
        equipment_angular_error_seconds=10.0,
    )
    defaults.update(kwargs)
    return ProjectData(**defaults)


def _obs(station: str, sighted_point: str, distance_m: float, angle_deg: float) -> TraverseObservation:
    return TraverseObservation(
        station=station,
        sighted_point=sighted_point,
        distance_m=distance_m,
        observed_angle_deg=angle_deg,
    )


# Square: 4 sides, 10 m each, all 90° interior angles
SQUARE_OBS = [
    _obs("A", "B", 10.0, 90.0),
    _obs("B", "C", 10.0, 90.0),
    _obs("C", "D", 10.0, 90.0),
    _obs("D", "A", 10.0, 90.0),
]



def test_angular_closure_perfect():
    result = compute_planimetry_traverse(
        [PlanimetryLeg("A", "B", 10.0, 90.0),
         PlanimetryLeg("B", "C", 10.0, 90.0),
         PlanimetryLeg("C", "D", 10.0, 90.0),
         PlanimetryLeg("D", "A", 10.0, 90.0)],
        initial_azimuth_deg=0.0,
    )
    assert abs(result.angular_misclosure_seconds) < 1e-6



def test_angular_closure_distributed():
    # Add 4" total misclosure (1" per side after distribution)
    deg_offset = 4.0 / 3600.0  # 4 seconds in degrees, spread over 4 sides
    legs = [
        PlanimetryLeg("A", "B", 10.0, 90.0 + deg_offset),
        PlanimetryLeg("B", "C", 10.0, 90.0),
        PlanimetryLeg("C", "D", 10.0, 90.0),
        PlanimetryLeg("D", "A", 10.0, 90.0),
    ]
    result = compute_planimetry_traverse(legs, initial_azimuth_deg=0.0)
    # After correction, each leg should be adjusted by -1"
    assert abs(result.applied_angle_correction_seconds) > 0
    assert abs(result.angular_misclosure_seconds) > 0



def test_angular_tolerance_ok():
    # 4 sides, equipment error 10", tolerance = 10*4 = 40"
    # misclosure = 0 → should be ok
    project = _project(equipment_angular_error_seconds=10.0)
    result = process_traverse(SQUARE_OBS, project)
    ang = result.traverse_angular_summary
    assert ang is not None
    assert ang.status == "ok"
    assert ang.n_sides == 4
    assert abs(ang.allowed_error_seconds - 10.0 * 4) < 1e-9



def test_angular_tolerance_warning():
    # Use very tight tolerance (0.001") to force warning
    project = _project(equipment_angular_error_seconds=0.001)
    # Add a small misclosure by offsetting one angle
    obs = [
        _obs("A", "B", 10.0, 90.0 + 1.0 / 3600),  # +1" extra
        _obs("B", "C", 10.0, 90.0),
        _obs("C", "D", 10.0, 90.0),
        _obs("D", "A", 10.0, 90.0),
    ]
    result = process_traverse(obs, project)
    ang = result.traverse_angular_summary
    assert ang is not None
    assert ang.status == "warning"



def test_angular_tolerance_not_informed():
    project = _project(equipment_angular_error_seconds=None)
    result = process_traverse(SQUARE_OBS, project)
    ang = result.traverse_angular_summary
    assert ang is not None
    assert ang.status == "nao_informado"
    assert ang.allowed_error_seconds is None



def test_azimuth_propagation():
    legs = [PlanimetryLeg("A", "B", 10.0, 90.0)] * 4
    result_0 = compute_planimetry_traverse(legs, initial_azimuth_deg=0.0)
    result_45 = compute_planimetry_traverse(legs, initial_azimuth_deg=45.0)
    # First segment azimuth should equal initial_azimuth
    assert abs(result_0.segments[0].azimuth_deg - 0.0) < 1e-6
    assert abs(result_45.segments[0].azimuth_deg - 45.0) < 1e-6



def test_bearing_quadrants():
    from app.services.planimetry import azimuth_to_quadrant_bearing
    assert "NE" in azimuth_to_quadrant_bearing(45.0)
    assert "SE" in azimuth_to_quadrant_bearing(135.0)
    assert "SW" in azimuth_to_quadrant_bearing(225.0)
    assert "NW" in azimuth_to_quadrant_bearing(315.0)



def test_projections():
    legs = [
        PlanimetryLeg("A", "B", 10.0, 90.0),
        PlanimetryLeg("B", "C", 10.0, 90.0),
        PlanimetryLeg("C", "D", 10.0, 90.0),
        PlanimetryLeg("D", "A", 10.0, 90.0),
    ]
    result = compute_planimetry_traverse(legs, initial_azimuth_deg=0.0, minimize_projection_closure=False)
    for seg in result.segments:
        expected_e = 10.0 * math.sin(math.radians(seg.azimuth_deg))
        expected_n = 10.0 * math.cos(math.radians(seg.azimuth_deg))
        assert abs(seg.delta_e_m - expected_e) < 1e-6
        assert abs(seg.delta_n_m - expected_n) < 1e-6



def test_bowditch_correction_sums_to_zero():
    # Bowditch rule: sum(correction) = -closure, so sum(adjusted_delta) = 0
    obs = [
        _obs("A", "B", 10.0, 72.0),
        _obs("B", "C", 11.0, 72.0),
        _obs("C", "D", 9.0, 72.0),
        _obs("D", "E", 10.5, 72.0),
        _obs("E", "A", 10.0, 72.0),
    ]
    result = process_traverse(obs, _project())
    segments = result.segments
    # After Bowditch adjustment the adjusted projections must sum to zero
    sum_adj_e = sum(s.adjusted_delta_e_m for s in segments)
    sum_adj_n = sum(s.adjusted_delta_n_m for s in segments)
    assert abs(sum_adj_e) < 1e-9
    assert abs(sum_adj_n) < 1e-9



def test_area_square():
    result = process_traverse(SQUARE_OBS, _project())
    assert abs(result.area_m2 - 100.0) < 1e-6



def test_perimeter():
    result = process_traverse(SQUARE_OBS, _project())
    assert abs(result.perimeter_m - 40.0) < 1e-9



def test_minimum_3_sides_raise():
    obs = [_obs("A", "B", 10.0, 90.0), _obs("B", "A", 10.0, 90.0)]
    with pytest.raises(ValueError, match="3"):
        process_traverse(obs, _project())



def test_invalid_distance_raises():
    obs = [
        _obs("A", "B", -5.0, 90.0),
        _obs("B", "C", 10.0, 90.0),
        _obs("C", "A", 10.0, 90.0),
    ]
    with pytest.raises(ValueError):
        process_traverse(obs, _project())



def test_memorial_text_generated():
    project = _project(property_name="Fazenda Teste", owner_name="João Silva")
    result = process_traverse(SQUARE_OBS, project)
    assert result.memorial_text
    assert "FAZENDA TESTE" in result.memorial_text



def test_project_data_no_tolerance_fields():
    project = _project()
    assert not hasattr(project, "closure_tolerance_m")
    assert not hasattr(project, "equipment_linear_error_m")
    assert not hasattr(project, "distance_precision_m")
    assert not hasattr(project, "angle_error_limit_seconds")
    assert not hasattr(project, "irradiation_angle_error_seconds")
    assert not hasattr(project, "angular_precision_seconds")



def test_build_project_data_simplified():
    raw = {
        "property_name": "Lote A",
        "owner_name": "Maria",
        "municipality": "Campinas",
        "state": "SP",
        "datum": "SIRGAS2000",
        "coordinate_system": "UTM",
        "measurement_mode": "planimetrico",
        "equipment_angular_error_seconds": "10",
    }
    pd = build_project_data(raw)
    assert pd.measurement_mode == "planimetrico"
    assert pd.equipment_angular_error_seconds == 10.0
    assert not hasattr(pd, "closure_tolerance_m")



def test_traverse_returns_planimetric_table():
    result = process_traverse(SQUARE_OBS, _project())
    assert result.planimetric_table is not None
    assert len(result.planimetric_table.segments) == 4



def test_traverse_angular_summary_present():
    result = process_traverse(SQUARE_OBS, _project())
    assert result.traverse_angular_summary is not None
    assert result.traverse_angular_summary.n_sides == 4



def test_adjusted_points_count():
    result = process_traverse(SQUARE_OBS, _project())
    # adjusted_points: A, B, C, D, A (closed) → 5 entries
    assert len(result.adjusted_points) == len(SQUARE_OBS) + 1



def test_segments_count_matches_observations():
    result = process_traverse(SQUARE_OBS, _project())
    assert len(result.segments) == len(SQUARE_OBS)
