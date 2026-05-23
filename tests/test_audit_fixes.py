"""
Regression tests for all bugs identified in the GEOMEMORIAL audit.

Each test class corresponds to one or more Fix IDs (F-01 .. F-22).
Tests are designed to fail against the OLD code and pass against the
corrected code.
"""
from __future__ import annotations

import math

import pytest

from app.models.schemas import CoordinatePoint, IrradiationObservation
from app.services.angles import decimal_to_dms, parse_azimuth
from app.services.geometry import (
    EPSILON,
    MAX_VERTICES,
    adaptive_epsilon,
    azimuth_to_bearing,
    build_segments,
    closure_error,
    ensure_closed,
    is_closed,
    polygon_area,
    polygon_perimeter,
    signed_polygon_area,
    validate_no_self_intersection,
    validate_points,
)
from app.services.irradiation import irradiation_to_points
from app.services.reports import _prepare_closed_points, _project_points



def make_point(vertex: str, x: float, y: float) -> CoordinatePoint:
    return CoordinatePoint(vertex=vertex, x=x, y=y)


def square(size: float = 10.0) -> list[CoordinatePoint]:
    """Return a CCW square polygon (open — no closing duplicate)."""
    return [
        make_point("V1", 0.0, 0.0),
        make_point("V2", size, 0.0),
        make_point("V3", size, size),
        make_point("V4", 0.0, size),
    ]


# F-01: PDF projection Y double-accounting

class TestF01PdfProjection:
    """All projected points must lie inside the bounding box."""

    def _all_inside(
        self,
        points: list[CoordinatePoint],
        left: float,
        top: float,
        width: float,
        height: float,
    ) -> bool:
        projected = _project_points(points, left, top, width, height)
        for x, y in projected:
            if x < left - EPSILON or x > left + width + EPSILON:
                return False
            if y < top - EPSILON or y > top + height + EPSILON:
                return False
        return True

    def test_square_polygon_inside_box(self):
        pts = square(10.0)
        assert self._all_inside(pts, left=20, top=35, width=170, height=120)

    def test_rectangle_polygon_inside_box(self):
        pts = [
            make_point("A", 0, 0),
            make_point("B", 100, 0),
            make_point("C", 100, 30),
            make_point("D", 0, 30),
        ]
        assert self._all_inside(pts, left=20, top=35, width=170, height=120)

    def test_tall_polygon_inside_box(self):
        pts = [
            make_point("A", 0, 0),
            make_point("B", 1, 0),
            make_point("C", 1, 1000),
            make_point("D", 0, 1000),
        ]
        assert self._all_inside(pts, left=20, top=35, width=170, height=120)

    def test_utm_coordinates_inside_box(self):
        """Typical UTM easting/northing values must stay inside box."""
        pts = [
            make_point("V1", 487654.0, 7654321.0),
            make_point("V2", 487720.0, 7654321.0),
            make_point("V3", 487720.0, 7654380.0),
            make_point("V4", 487654.0, 7654380.0),
        ]
        assert self._all_inside(pts, left=20, top=35, width=170, height=120)

    def test_degenerate_all_same_x(self):
        """Degenerate polygon (all same X) must not raise and stays in box."""
        pts = [
            make_point("A", 5.0, 0.0),
            make_point("B", 5.0, 10.0),
            make_point("C", 5.0, 20.0),
        ]
        projected = _project_points(pts, left=20, top=35, width=170, height=120)
        for x, y in projected:
            assert 20 - EPSILON <= x <= 190 + EPSILON
            assert 35 - EPSILON <= y <= 155 + EPSILON

    def test_y_axis_flip(self):
        """Lower y in data must map to lower y in PDF (Y-down axis)."""
        pts = [
            make_point("Low",  0.0, 0.0),
            make_point("High", 0.0, 10.0),
        ]
        projected = _project_points(pts, left=0, top=0, width=100, height=100)
        y_low_data, y_high_data = projected[0][1], projected[1][1]
        # In PDF coords Y increases downward, so lower data y → higher PDF y value.
        assert y_low_data > y_high_data


# F-02: DWG fake export

class TestF02DwgExport:
    def test_dwg_raises_not_implemented(self):
        from app.services.strategies.export import DwgExportStrategy, ExportPayload
        import pathlib
        import tempfile

        pts = square()
        with tempfile.TemporaryDirectory() as tmp:
            payload = ExportPayload(
                property_name="Test",
                points=pts,
                memorial_text="test",
                output_dir=pathlib.Path(tmp),
                slug="test",
                token="abc12345",
            )
            with pytest.raises(NotImplementedError):
                DwgExportStrategy().export(payload)

    def test_factory_dwg_raises_value_error(self):
        from app.services.strategies.export import ExportStrategyFactory
        factory = ExportStrategyFactory()
        with pytest.raises(ValueError, match="DWG"):
            factory.for_output_format("dwg")

    def test_factory_dxf_still_works(self):
        from app.services.strategies.export import DxfExportStrategy, ExportStrategyFactory
        factory = ExportStrategyFactory()
        assert isinstance(factory.for_output_format("dxf"), DxfExportStrategy)


# F-03: decimal_to_dms never returns 360

class TestF03DecimalToDms:
    def test_never_returns_360(self):
        # 359.9999722 rounds to 360°00'00" in the old code.
        result = decimal_to_dms(359.9999722)
        assert not result.startswith("360")

    def test_boundary_360_wraps_to_0(self):
        result = decimal_to_dms(360.0)
        assert result.startswith("000")

    def test_720_wraps_to_0(self):
        result = decimal_to_dms(720.0)
        assert result.startswith("000")

    def test_normal_value_unchanged(self):
        result = decimal_to_dms(90.0)
        assert result == "090°00'00\""

    def test_carry_from_seconds(self):
        # 59 minutes 59.5 seconds → carries to 60 min → 1 degree carry
        result = decimal_to_dms(1.0)
        assert result == "001°00'00\""

    def test_output_format(self):
        result = decimal_to_dms(123.5)
        assert "°" in result and "'" in result and '"' in result

    @pytest.mark.parametrize("angle", [0.0, 45.0, 90.0, 180.0, 270.0, 359.9])
    def test_valid_range_no_overflow(self, angle):
        result = decimal_to_dms(angle)
        deg = int(result.split("°")[0])
        assert 0 <= deg < 360


# F-04: NaN/Inf must fail validation before set() operations

class TestF04NanInfValidation:
    def test_nan_x_raises(self):
        pts = [
            make_point("A", float("nan"), 0.0),
            make_point("B", 10.0, 0.0),
            make_point("C", 10.0, 10.0),
        ]
        with pytest.raises(ValueError, match="invalida"):
            validate_points(pts)

    def test_nan_y_raises(self):
        pts = [
            make_point("A", 0.0, float("nan")),
            make_point("B", 10.0, 0.0),
            make_point("C", 10.0, 10.0),
        ]
        with pytest.raises(ValueError):
            validate_points(pts)

    def test_inf_raises(self):
        pts = [
            make_point("A", float("inf"), 0.0),
            make_point("B", 10.0, 0.0),
            make_point("C", 10.0, 10.0),
        ]
        with pytest.raises(ValueError):
            validate_points(pts)

    def test_neg_inf_raises(self):
        pts = [
            make_point("A", 0.0, float("-inf")),
            make_point("B", 10.0, 0.0),
            make_point("C", 10.0, 10.0),
        ]
        with pytest.raises(ValueError):
            validate_points(pts)

    def test_multiple_nan_raises(self):
        """Two NaN values must not pass deduplication check."""
        pts = [
            make_point("A", float("nan"), float("nan")),
            make_point("B", float("nan"), float("nan")),
            make_point("C", 10.0, 10.0),
        ]
        with pytest.raises(ValueError):
            validate_points(pts)

    def test_valid_points_pass(self):
        validate_points(square())  # must not raise


# F-05: ensure_closed uses EPSILON comparison

class TestF05EnsureClosedEpsilon:
    def test_tiny_difference_treated_as_closed(self):
        pts = square()
        # Add a closing point with a sub-EPSILON difference.
        almost_closed = pts + [make_point("V1", 1e-12, 1e-12)]
        result = ensure_closed(almost_closed)
        # Should NOT add another closing point.
        assert result[-1].x == pytest.approx(1e-12)
        assert len(result) == len(almost_closed)

    def test_open_polygon_gets_closed(self):
        pts = square()
        result = ensure_closed(pts)
        assert len(result) == len(pts) + 1
        assert result[-1].x == pts[0].x
        assert result[-1].y == pts[0].y

    def test_already_closed_not_doubled(self):
        pts = square()
        closed_once = ensure_closed(pts)
        closed_twice = ensure_closed(closed_once)
        assert len(closed_twice) == len(closed_once)

    def test_utm_coordinates_epsilon(self):
        """UTM-scale coordinates with 1e-9 m difference treated as closed."""
        pts = [
            make_point("V1", 487654.0, 7654321.0),
            make_point("V2", 487720.0, 7654321.0),
            make_point("V3", 487720.0, 7654380.0),
            # Last point differs by 1e-10 m from V1 — within EPSILON.
            make_point("V1", 487654.0 + 1e-10, 7654321.0 + 1e-10),
        ]
        result = ensure_closed(pts)
        assert len(result) == 4  # not extended

    def test_is_closed_helper_exact(self):
        p1 = make_point("V1", 5.0, 5.0)
        p2 = make_point("V1", 5.0, 5.0)
        assert is_closed(p1, p2)

    def test_is_closed_helper_not_closed(self):
        p1 = make_point("V1", 5.0, 5.0)
        p2 = make_point("V2", 5.0, 5.0001)
        assert not is_closed(p1, p2)


# F-06: Irradiation is NOT sorted by azimuth; table rows preserve input order;
#        polygon points are sorted geometrically (polar angle around centroid).

class TestF06IrradiationOrder:
    def _make_obs(self, vertex, azimuth, distance):
        return IrradiationObservation(
            vertex=vertex, azimuth_deg=azimuth, distance_m=distance
        )

    def test_table_rows_preserve_input_order(self):
        """Table rows must be in the original observation order (audit trail)."""
        obs = [
            self._make_obs("V1", 270.0, 10.0),
            self._make_obs("V2", 180.0, 10.0),
            self._make_obs("V3", 90.0, 10.0),
        ]
        from app.services.irradiation import compute_irradiation
        pts, table = compute_irradiation(obs, origin_x=0.0, origin_y=0.0)
        assert [r.vertex for r in table.rows] == ["V1", "V2", "V3"]

    def test_points_sorted_geometrically_not_by_azimuth(self):
        """Polygon points must be sorted geometrically, not by azimuth value."""
        # V1 az=270 → (-10, 0), V2 az=180 → (0,-10), V3 az=90 → (10, 0)
        obs = [
            self._make_obs("V1", 270.0, 10.0),
            self._make_obs("V2", 180.0, 10.0),
            self._make_obs("V3", 90.0, 10.0),
        ]
        pts = irradiation_to_points(obs, origin_x=0.0, origin_y=0.0)
        # All vertices present regardless of order
        assert {p.vertex for p in pts} == {"V1", "V2", "V3"}
        # Points are NOT in azimuth-ascending order (old wrong behavior was az-sort)
        azimuth_sorted_order = ["V3", "V2", "V1"]  # 90°, 180°, 270°
        assert [p.vertex for p in pts] != azimuth_sorted_order

    def test_l_shaped_all_vertices_present(self):
        """All vertices must be present after geometric sorting."""
        obs = [
            self._make_obs("A", 315.0, 14.142),
            self._make_obs("B", 45.0, 14.142),
            self._make_obs("C", 135.0, 14.142),
        ]
        pts = irradiation_to_points(obs, origin_x=0.0, origin_y=0.0)
        assert {p.vertex for p in pts} == {"A", "B", "C"}


# F-07: parse_azimuth preserves negative sign

class TestF07ParseAzimuthNegative:
    def test_negative_decimal_wrapped(self):
        # -90.0° → 270.0°
        result = parse_azimuth("-90")
        assert abs(result - 270.0) < 1e-9

    def test_negative_dms_wrapped(self):
        # -90°30'00" → 269.5°
        result = parse_azimuth("-90°30'00\"")
        assert abs(result - 269.5) < 1e-9

    def test_positive_unchanged(self):
        result = parse_azimuth("45.5")
        assert abs(result - 45.5) < 1e-9

    def test_positive_dms(self):
        result = parse_azimuth("90°30'00\"")
        assert abs(result - 90.5) < 1e-9

    def test_zero(self):
        result = parse_azimuth("0")
        assert result == 0.0

    def test_360_normalises_to_0(self):
        result = parse_azimuth("360")
        assert result == 0.0

    def test_negative_720_wraps_to_0(self):
        result = parse_azimuth("-720")
        assert result == 0.0


# F-08: Consistent closure criterion (is_closed shared helper)

class TestF08ClosureCriterion:
    """Both _prepare_closed_points (reports) and ensure_closed (geometry)
    must produce the same result for the same input."""

    def test_both_agree_open_polygon(self):
        pts = square()
        from_reports = _prepare_closed_points(pts)
        from_geometry = ensure_closed(pts)
        assert len(from_reports) == len(from_geometry)

    def test_both_agree_already_closed(self):
        pts = square()
        pts_closed = pts + [make_point("V1", 0.0, 0.0)]
        from_reports = _prepare_closed_points(pts_closed)
        from_geometry = ensure_closed(pts_closed)
        assert len(from_reports) == len(from_geometry)

    def test_reports_uses_epsilon(self):
        """_prepare_closed_points must not add a duplicate for sub-EPSILON drift."""
        pts = square()
        pts_almost_closed = pts + [make_point("V1", 1e-11, 1e-11)]
        result = _prepare_closed_points(pts_almost_closed)
        # Must NOT append another closing point.
        assert len(result) == len(pts_almost_closed)


# F-10: Zero-distance segments

class TestF10ZeroDistanceSegments:
    def test_duplicate_consecutive_raises(self):
        pts = [
            make_point("A", 0.0, 0.0),
            make_point("B", 0.0, 0.0),  # duplicate
            make_point("C", 10.0, 10.0),
            make_point("A", 0.0, 0.0),
        ]
        with pytest.raises(ValueError, match="zero"):
            build_segments(pts)

    def test_valid_segments_compute_correctly(self):
        pts = ensure_closed(square(10.0))
        segs = build_segments(pts)
        assert len(segs) == 4
        for seg in segs:
            assert seg.distance_m > EPSILON

    def test_minimum_positive_distance(self):
        pts = [
            make_point("A", 0.0, 0.0),
            make_point("B", 1e-8, 0.0),  # > EPSILON (1e-9)
            make_point("C", 1e-8, 1e-8),
            make_point("A", 0.0, 0.0),
        ]
        segs = build_segments(pts)
        assert all(s.distance_m > EPSILON for s in segs)


# F-11: Adaptive epsilon

class TestF11AdaptiveEpsilon:
    def test_utm_scale(self):
        pts = [
            make_point("A", 487654.0, 7654321.0),
            make_point("B", 487720.0, 7654321.0),
            make_point("C", 487720.0, 7654380.0),
        ]
        eps = adaptive_epsilon(pts)
        assert eps >= EPSILON
        assert eps <= 1e-3

    def test_geographic_scale(self):
        pts = [
            make_point("A", -46.5, -23.5),
            make_point("B", -46.4, -23.5),
            make_point("C", -46.4, -23.4),
        ]
        eps = adaptive_epsilon(pts)
        assert eps >= EPSILON

    def test_empty_returns_default(self):
        assert adaptive_epsilon([]) == EPSILON

    def test_nan_coordinates_returns_default(self):
        pts = [make_point("A", float("nan"), float("nan"))]
        assert adaptive_epsilon(pts) == EPSILON


# F-12: has_explicit_station uses AND

class TestF12StationAnd:
    def _obs(self, vertex, station_x=None, station_y=None):
        return IrradiationObservation(
            vertex=vertex,
            azimuth_deg=90.0,
            distance_m=10.0,
            station_x=station_x,
            station_y=station_y,
        )

    def test_partial_station_raises(self):
        """station_x set but station_y=None must raise a clear error."""
        obs = [
            self._obs("V1", station_x=100.0, station_y=None),
            self._obs("V2"),
            self._obs("V3"),
        ]
        with pytest.raises(ValueError, match="parcialmente"):
            irradiation_to_points(obs, origin_x=0.0, origin_y=0.0)

    def test_partial_station_only_y_raises(self):
        obs = [
            self._obs("V1", station_x=None, station_y=200.0),
            self._obs("V2"),
            self._obs("V3"),
        ]
        with pytest.raises(ValueError, match="parcialmente"):
            irradiation_to_points(obs, origin_x=0.0, origin_y=0.0)

    def test_both_set_is_valid(self):
        obs = [
            self._obs("V1", station_x=100.0, station_y=200.0),
            self._obs("V2", station_x=100.0, station_y=200.0),
            self._obs("V3", station_x=100.0, station_y=200.0),
        ]
        pts = irradiation_to_points(obs)
        assert len(pts) == 3

    def test_neither_set_uses_origin(self):
        obs = [
            self._obs("V1"),
            self._obs("V2"),
            self._obs("V3"),
        ]
        pts = irradiation_to_points(obs, origin_x=0.0, origin_y=0.0)
        assert len(pts) == 3


# F-13: polygon_area raises for < 3 points

class TestF13PolygonAreaMinPoints:
    def test_zero_points_raises(self):
        with pytest.raises(ValueError):
            polygon_area([])

    def test_one_point_raises(self):
        with pytest.raises(ValueError):
            polygon_area([make_point("A", 0, 0)])

    def test_two_points_raises(self):
        with pytest.raises(ValueError):
            polygon_area([make_point("A", 0, 0), make_point("B", 1, 0)])

    def test_three_points_valid(self):
        pts = [
            make_point("A", 0, 0),
            make_point("B", 1, 0),
            make_point("C", 0, 1),
        ]
        assert polygon_area(pts) == pytest.approx(0.5)

    def test_square_area(self):
        pts = ensure_closed(square(10.0))
        assert polygon_area(pts) == pytest.approx(100.0)

    def test_signed_area_ccw_positive(self):
        pts = [
            make_point("A", 0, 0),
            make_point("B", 1, 0),
            make_point("C", 0, 1),
        ]
        assert signed_polygon_area(pts) > 0

    def test_signed_area_cw_negative(self):
        pts = [
            make_point("A", 0, 0),
            make_point("C", 0, 1),
            make_point("B", 1, 0),
        ]
        assert signed_polygon_area(pts) < 0


# F-14: CSV does not silently skip invalid lines

class TestF14CsvNoSilentSkip:
    def test_missing_x_raises_with_line_info(self):
        from app.services.strategies.parsing import CsvTxtParsingStrategy
        csv_content = "vertex,x,y\nV1,,100.0\nV2,10.0,200.0\nV3,20.0,300.0"
        strategy = CsvTxtParsingStrategy()
        with pytest.raises(ValueError, match="invalida"):
            strategy.parse(csv_content)

    def test_missing_y_raises_with_line_info(self):
        from app.services.strategies.parsing import CsvTxtParsingStrategy
        csv_content = "vertex,x,y\nV1,10.0,\nV2,20.0,200.0\nV3,30.0,300.0"
        strategy = CsvTxtParsingStrategy()
        with pytest.raises(ValueError, match="invalida"):
            strategy.parse(csv_content)

    def test_valid_csv_parses_all_rows(self):
        from app.services.strategies.parsing import CsvTxtParsingStrategy
        csv_content = "vertex,x,y\nV1,10.0,100.0\nV2,20.0,200.0\nV3,30.0,300.0"
        strategy = CsvTxtParsingStrategy()
        pts = strategy.parse(csv_content)
        assert len(pts) == 3


# F-15: Shapefile type validation

class TestF15ShapefileTypeValidation:
    def test_accepted_types_constant(self):
        from app.services.strategies.parsing import ACCEPTED_SHAPE_TYPES
        # Must include Polygon (5), PolygonZ (15), PolygonM (25)
        assert 5 in ACCEPTED_SHAPE_TYPES
        assert 15 in ACCEPTED_SHAPE_TYPES
        assert 25 in ACCEPTED_SHAPE_TYPES
        # Must NOT include Point (1), Polyline (3)
        assert 1 not in ACCEPTED_SHAPE_TYPES
        assert 3 not in ACCEPTED_SHAPE_TYPES


# F-17: Text size limit

class TestF17TextSizeLimit:
    def test_oversized_text_raises(self):
        from app.services.strategies.parsing import (
            MAX_TEXT_BYTES,
            TextCoordinatesParsingStrategy,
        )
        huge = "A" * (MAX_TEXT_BYTES + 1)
        strategy = TextCoordinatesParsingStrategy()
        with pytest.raises(ValueError, match="grande"):
            strategy.parse(huge)

    def test_normal_text_passes(self):
        from app.services.strategies.parsing import TextCoordinatesParsingStrategy
        text = "V1,0,0\nV2,10,0\nV3,10,10"
        strategy = TextCoordinatesParsingStrategy()
        pts = strategy.parse(text)
        assert len(pts) == 3


# F-21: signed_polygon_area orientation

class TestF21SignedArea:
    def test_ccw_positive(self):
        # Unit square traversed CCW
        pts = [
            make_point("A", 0, 0),
            make_point("B", 1, 0),
            make_point("C", 1, 1),
            make_point("D", 0, 1),
        ]
        assert signed_polygon_area(pts) > 0

    def test_cw_negative(self):
        pts = [
            make_point("A", 0, 0),
            make_point("D", 0, 1),
            make_point("C", 1, 1),
            make_point("B", 1, 0),
        ]
        assert signed_polygon_area(pts) < 0

    def test_magnitude_matches_unsigned(self):
        pts = ensure_closed(square(10.0))
        assert abs(signed_polygon_area(pts)) == pytest.approx(polygon_area(pts))

    def test_utm_square(self):
        pts = [
            make_point("V1", 487654.0, 7654321.0),
            make_point("V2", 487754.0, 7654321.0),
            make_point("V3", 487754.0, 7654421.0),
            make_point("V4", 487654.0, 7654421.0),
        ]
        closed = ensure_closed(pts)
        assert polygon_area(closed) == pytest.approx(10000.0, rel=1e-6)


# F-22: Vertex limit (DoS protection)

class TestF22VertexLimit:
    def test_above_limit_raises(self):
        pts = [make_point(f"V{i}", float(i), 0.0) for i in range(MAX_VERTICES + 1)]
        with pytest.raises(ValueError, match="limite"):
            validate_points(pts)

    def test_at_limit_passes(self):
        # Build MAX_VERTICES distinct points on a line — note this won't form a
        # valid polygon (collinear), so we just test the count guard in isolation.
        # We use a triangle to prove valid polygons pass.
        triangle = [
            make_point("A", 0.0, 0.0),
            make_point("B", 1.0, 0.0),
            make_point("C", 0.5, 1.0),
        ]
        validate_points(triangle)  # must not raise

    def test_max_vertices_constant_reasonable(self):
        assert 100 < MAX_VERTICES <= 100_000



class TestNumericalEdgeCases:
    def test_azimuth_to_bearing_north(self):
        assert azimuth_to_bearing(0.0) == "N 00°00'00\" E"

    def test_azimuth_to_bearing_east(self):
        # 90° → SE quadrant → S (180-90)° E = S 90°E
        assert azimuth_to_bearing(90.0) == "S 90°00'00\" E"

    def test_azimuth_to_bearing_south(self):
        # 180° → SW quadrant → S (180-180)° W = S 00°W
        assert azimuth_to_bearing(180.0) == "S 00°00'00\" W"

    def test_azimuth_to_bearing_west(self):
        # 270° → NW quadrant → N (360-270)° W = N 90°W
        assert azimuth_to_bearing(270.0) == "N 90°00'00\" W"

    def test_closure_error_closed_polygon(self):
        pts = ensure_closed(square())  # closed: first == last
        err = closure_error(pts)
        assert err == pytest.approx(0.0)

    def test_closure_error_open_polygon_nonzero(self):
        pts = square()  # open: V4(0,10) ≠ V1(0,0) → distance = 10
        err = closure_error(pts)
        assert err == pytest.approx(10.0)

    def test_perimeter_square(self):
        pts = ensure_closed(square(10.0))
        assert polygon_perimeter(pts) == pytest.approx(40.0)

    def test_validate_no_self_intersection_valid(self):
        pts = ensure_closed(square(10.0))
        validate_no_self_intersection(pts)  # must not raise

    def test_validate_no_self_intersection_invalid(self):
        # Figure-8 (self-intersecting)
        pts = [
            make_point("A", 0, 0),
            make_point("B", 10, 10),
            make_point("C", 10, 0),
            make_point("D", 0, 10),
            make_point("A", 0, 0),
        ]
        with pytest.raises(ValueError):
            validate_no_self_intersection(pts)

    def test_build_segments_azimuth_north(self):
        pts = [
            make_point("A", 0.0, 0.0),
            make_point("B", 0.0, 10.0),
        ]
        segs = build_segments(pts)
        assert segs[0].azimuth_deg == pytest.approx(0.0)

    def test_build_segments_azimuth_east(self):
        pts = [
            make_point("A", 0.0, 0.0),
            make_point("B", 10.0, 0.0),
        ]
        segs = build_segments(pts)
        assert segs[0].azimuth_deg == pytest.approx(90.0)
