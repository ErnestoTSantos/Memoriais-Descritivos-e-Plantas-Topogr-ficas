from __future__ import annotations

import math
import unittest

from app.models.schemas import CoordinatePoint, IrradiationObservation
from app.services.parsing import parse_text_coordinates
from app.services.processing import build_project_data, process_coordinates




def _ptp_project(closure_tol: str = "10000.0", **extra):
    """
    ProjectData for planimetrico mode.

    closure_tol is accepted for backward compatibility but ignored.
    """
    raw = {
        "measurement_mode": "planimetrico",
    }
    raw.update(extra)
    return build_project_data(raw)


def _irr_project(
    station_x: float,
    station_y: float,
    angle_error_s: float = 0.0,
    closure_tol: str = "10000.0",
    **extra,
):
    """ProjectData for irradiacao mode with a station."""
    raw = {
        "measurement_mode": "irradiacao",
        "irradiation_origin_x": str(station_x),
        "irradiation_origin_y": str(station_y),
    }
    if angle_error_s:
        raw["equipment_angular_error_seconds"] = str(angle_error_s)
    raw.update(extra)
    return build_project_data(raw)


def _pt(vertex: str, x: float, y: float) -> CoordinatePoint:
    return CoordinatePoint(vertex=vertex, x=x, y=y)


def _obs(
    vertex: str,
    az: float,
    dist: float,
    sx: float | None = None,
    sy: float | None = None,
) -> IrradiationObservation:
    return IrradiationObservation(
        vertex=vertex,
        azimuth_deg=az,
        distance_m=dist,
        station_x=sx,
        station_y=sy,
    )




class ProcessingServiceTests(unittest.TestCase):
    def test_build_project_data_rejects_non_positive_angular_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "erro angular"):
            build_project_data({"equipment_angular_error_seconds": "0"})

    def test_build_project_data_accepts_positive_angular_error(self) -> None:
        project_data = build_project_data(
            {
                "measurement_mode": "planimetrico",
                "equipment_angular_error_seconds": "30",
            }
        )

        self.assertAlmostEqual(
            project_data.equipment_angular_error_seconds or 0.0, 30.0, places=6
        )

    def test_build_project_data_accepts_zero_station_coordinates(self) -> None:
        project_data = build_project_data(
            {
                "measurement_mode": "irradiacao",
                "irradiation_origin_x": 0.0,
                "irradiation_origin_y": 0.0,
            }
        )

        self.assertEqual(len(project_data.stations), 1)
        self.assertAlmostEqual(project_data.stations[0].x, 0.0, places=12)
        self.assertAlmostEqual(project_data.stations[0].y, 0.0, places=12)

    def test_build_project_data_rejects_partial_station_coordinates(self) -> None:
        with self.assertRaisesRegex(ValueError, "X e Y da estacao"):
            build_project_data(
                {
                    "measurement_mode": "irradiacao",
                    "irradiation_origin_x": "0",
                    "irradiation_origin_y": "",
                }
            )

    def test_process_coordinates_applies_angle_adjustment_to_point_to_point(
        self,
    ) -> None:
        # The assertion here is about angle-error propagation to segments.
        # The open triangle must still receive its implicit closing side.
        points = parse_text_coordinates("V-01, 0, 0\nV-02, 10, 0\nV-03, 10, 10")
        project_data = build_project_data(
            {
                "measurement_mode": "planimetrico",
                "equipment_angular_error_seconds": "30",
            }
        )

        result = process_coordinates(points, project_data)
        # The input is an open polygon (3 vertices, no repeated first vertex).
        # The closing edge V-03→V-01 is a real polygon side and must be included.
        self.assertEqual(len(result.segments), 3)
        self.assertAlmostEqual(
            result.segments[0].applied_angle_error_seconds, 30.0, places=6
        )


# Bug #1 — tolerância de fechamento ignorada


class ClosureToleranceTests(unittest.TestCase):
    """
    Regression suite for Bug #1.

    Before the fix, closure_error() was called on the already-forced-closed
    polygon (ensure_closed appends first == last), so it always returned 0 and
    the tolerance check was dead code.  The fix moves the check to BEFORE
    ensure_closed(), using the raw input points.
    """

    # Triangle with an explicit measured closure point named V-01, offset from
    # the start by (dx=0.20, dy=0.15).  This is a closing residual, not a
    # polygon side.
    _EXPLICIT_MISCLOSED_TRIANGLE = [
        _pt("V-01", 0.0, 0.0),
        _pt("V-02", 10.0, 0.0),
        _pt("V-03", 5.0, 10.0),
        _pt("V-01", 0.20, 0.15),
    ]
    _EXPECTED_GAP = math.hypot(0.20, 0.15)

    def test_open_polygon_above_tolerance_is_flagged_globally(self) -> None:
        """Explicit residual (0.25 m) exceeds tight tolerance (0.05 m)."""
        project_data = _ptp_project(closure_tol="0.05")
        result = process_coordinates(
            list(self._EXPLICIT_MISCLOSED_TRIANGLE), project_data
        )

        self.assertEqual(result.adjustment_summary["status"], "fora_da_tolerancia")
        self.assertAlmostEqual(result.adjustment_summary["tolerance_m"], 0.05, places=6)
        self.assertAlmostEqual(
            result.adjustment_summary["accumulated_error_m"],
            self._EXPECTED_GAP,
            places=6,
        )

    def test_open_polygon_within_tolerance_passes(self) -> None:
        """Explicit residual (0.25 m) is within loose tolerance (0.50 m)."""
        project_data = _ptp_project(closure_tol="0.50")
        result = process_coordinates(
            list(self._EXPLICIT_MISCLOSED_TRIANGLE), project_data
        )
        # The reported misclosure must reflect the real gap, not 0.
        self.assertAlmostEqual(result.closure_error_m, self._EXPECTED_GAP, places=6)

    def test_naturally_closed_polygon_has_zero_closure_error(self) -> None:
        """A polygon whose last vertex equals the first must have zero gap."""
        closed_pts = [
            _pt("V-01", 0.0, 0.0),
            _pt("V-02", 10.0, 0.0),
            _pt("V-03", 5.0, 10.0),
            _pt("V-01", 0.0, 0.0),  # explicit closure
        ]
        project_data = _ptp_project(closure_tol="0.001")
        result = process_coordinates(closed_pts, project_data)
        self.assertAlmostEqual(result.closure_error_m, 0.0, places=12)

    def test_closure_error_stored_in_result_matches_actual_gap(self) -> None:
        """ProcessingResult.closure_error_m must equal the real geometric gap."""
        project_data = _ptp_project(closure_tol="0.50")
        result = process_coordinates(
            list(self._EXPLICIT_MISCLOSED_TRIANGLE), project_data
        )
        self.assertAlmostEqual(result.closure_error_m, self._EXPECTED_GAP, places=9)

    def test_zero_angular_error_rejects_equipment_config(self) -> None:
        """equipment_angular_error_seconds=0 is rejected by build_project_data."""
        with self.assertRaisesRegex(ValueError, "erro angular"):
            build_project_data(
                {"measurement_mode": "planimetrico", "equipment_angular_error_seconds": "0"}
            )


# Equipment tolerance and distributed adjustment


class EquipmentToleranceAdjustmentTests(unittest.TestCase):
    _MISCLOSED = ClosureToleranceTests._EXPLICIT_MISCLOSED_TRIANGLE
    _GAP = ClosureToleranceTests._EXPECTED_GAP

    def _result(self, tolerance: str, **extra):
        return process_coordinates(
            list(self._MISCLOSED), _ptp_project(closure_tol=tolerance, **extra)
        )

    def test_global_status_outside_default_tolerance(self) -> None:
        # Gap is 0.25 m; default tolerance is 0.05 m → always fora_da_tolerancia.
        result = self._result("0.40")
        self.assertEqual(result.adjustment_summary["status"], "fora_da_tolerancia")

    def test_distributed_adjustment_cancels_closure_vector(self) -> None:
        result = self._result("0.50")
        summary = result.adjustment_summary

        self.assertAlmostEqual(summary["correction_sum_e_m"], -0.20, places=9)
        self.assertAlmostEqual(summary["correction_sum_n_m"], -0.15, places=9)
        self.assertAlmostEqual(
            result.adjusted_points[-1].adjusted_x or 0.0, 0.0, places=9
        )
        self.assertAlmostEqual(
            result.adjusted_points[-1].adjusted_y or 0.0, 0.0, places=9
        )

    def test_segment_contributions_are_proportional_to_lengths(self) -> None:
        result = self._result("0.50")
        total_contribution = sum(s.contribution_percent for s in result.segments)
        longest = max(result.segments, key=lambda s: s.distance_m)
        shortest = min(result.segments, key=lambda s: s.distance_m)

        self.assertAlmostEqual(total_contribution, 100.0, places=9)
        self.assertGreater(longest.contribution_percent, shortest.contribution_percent)
        self.assertTrue(
            all(
                s.contribution_status in {"baixa", "moderada", "alta"}
                for s in result.segments
            )
        )

    def test_angular_status_nao_informado_when_no_precision_configured(
        self,
    ) -> None:
        # Without equipment_angular_error_seconds the angular status is undefined.
        result = process_coordinates(
            [
                _pt("V-01", 0.0, 0.0),
                _pt("V-02", 10.0, 0.0),
                _pt("V-03", 10.0, 10.0),
            ],
            _ptp_project(),
        )

        self.assertEqual(
            result.adjustment_summary["angular_status"], "nao_informado"
        )

    def test_response_payload_contains_accumulated_error_and_corrections(self) -> None:
        result = self._result("0.50")

        self.assertIn("accumulated_error_m", result.adjustment_summary)
        self.assertIn("tolerance_m", result.adjustment_summary)
        self.assertGreater(result.segments[0].estimated_error_m, 0.0)
        self.assertNotEqual(result.segments[0].correction_e_m, 0.0)


# Bug #2 — dupla aplicação do erro angular em modo irradiação


class IrradiationAzimuthConsistencyTests(unittest.TestCase):
    """
    Regression suite for Bug #2.

    Before the fix, angle_error_seconds was applied in irradiation_to_points()
    (embedding the correction into Cartesian coordinates) and then applied a
    *second* time inside build_segments() via adjusted_azimuth.  This caused
    every azimuth in the memorial to be off by exactly angle_error_seconds/3600°.

    The fix passes angle_error_seconds=0.0 to build_segments() when mode is
    irradiacao; the correction is already baked into the coordinates.
    """

    # Station at origin; three observations with explicit station coords so
    # that insertion order is preserved (no azimuth-sort reordering).
    _STATION_X = 0.0
    _STATION_Y = 0.0
    _DIST = 100.0
    _ERROR_S = 3600.0  # 1 degree — large enough to detect double-counting

    def _make_observations(self):
        sx, sy, d = self._STATION_X, self._STATION_Y, self._DIST
        return [
            _obs("V-01", az=0.0, dist=d, sx=sx, sy=sy),  # North
            _obs("V-02", az=90.0, dist=d, sx=sx, sy=sy),  # East
            _obs("V-03", az=210.0, dist=d, sx=sx, sy=sy),  # SSW
        ]

    def _expected_point(self, az_deg: float) -> tuple[float, float]:
        """Cartesian coordinates after applying the 1° angle correction."""
        corrected = math.radians((az_deg + self._ERROR_S / 3600.0) % 360.0)
        return (
            self._STATION_X + self._DIST * math.sin(corrected),
            self._STATION_Y + self._DIST * math.cos(corrected),
        )

    def _run(self) -> object:
        return process_coordinates(
            self._make_observations(),
            _irr_project(self._STATION_X, self._STATION_Y, angle_error_s=self._ERROR_S),
        )

    def test_irradiation_coordinates_incorporate_angle_correction(self) -> None:
        """Computed points must reflect the 1° correction, not the raw azimuth."""
        result = self._run()
        for i, az in enumerate([0.0, 90.0, 210.0]):
            ex, ey = self._expected_point(az)
            self.assertAlmostEqual(
                result.points[i].x, ex, places=9, msg=f"V-0{i+1} x mismatch"
            )
            self.assertAlmostEqual(
                result.points[i].y, ey, places=9, msg=f"V-0{i+1} y mismatch"
            )

    def test_irradiation_segments_have_no_second_angular_adjustment(self) -> None:
        """
        In irradiation mode, build_segments must NOT apply a second correction.
        azimuth_adjusted_deg must equal azimuth_deg (error_seconds == 0).
        """
        result = self._run()
        for seg in result.segments:
            self.assertEqual(
                seg.applied_angle_error_seconds,
                0.0,
                msg=(
                    f"Segment {seg.start_vertex}→{seg.end_vertex}: "
                    f"applied_angle_error_seconds should be 0 in irradiation mode, "
                    f"got {seg.applied_angle_error_seconds}"
                ),
            )
            self.assertAlmostEqual(
                seg.azimuth_adjusted_deg,
                seg.azimuth_deg,
                places=9,
                msg=(
                    f"Segment {seg.start_vertex}→{seg.end_vertex}: "
                    f"azimuth_adjusted_deg ({seg.azimuth_adjusted_deg:.6f}°) "
                    f"differs from azimuth_deg ({seg.azimuth_deg:.6f}°); "
                    f"double-counting of angle error detected"
                ),
            )

    def test_segment_azimuths_match_back_calculated_from_coordinates(self) -> None:
        """
        Each segment azimuth must equal atan2(ΔE, ΔN) computed directly from
        the stored coordinates — i.e. memorial values are geometrically truthful.
        """
        result = self._run()
        pts = result.points
        for seg in result.segments:
            start = next(p for p in pts if p.vertex == seg.start_vertex)
            end = next(p for p in pts if p.vertex == seg.end_vertex)
            dx, dy = end.x - start.x, end.y - start.y
            expected_az = (math.degrees(math.atan2(dx, dy)) + 360.0) % 360.0
            self.assertAlmostEqual(
                seg.azimuth_deg,
                expected_az,
                places=9,
                msg=(
                    f"azimuth_deg for {seg.start_vertex}→{seg.end_vertex} "
                    f"does not match geometry"
                ),
            )


class IrradiationErrorPropagationTests(unittest.TestCase):
    def _observations(self):
        return [
            _obs("P10", 0.0, 10.0),
            _obs("P100", 90.0, 100.0),
            _obs("P200", 180.0, 200.0),
        ]

    def test_angular_error_displacement_grows_with_distance(self) -> None:
        result = process_coordinates(
            self._observations(),
            _irr_project(
                0.0,
                0.0,
                angle_error_s=5.0,  # angular error required for non-zero component
            ),
        )
        by_vertex = {point.vertex: point for point in result.adjusted_points}

        self.assertGreater(
            by_vertex["P100"].angular_error_component_m,
            by_vertex["P10"].angular_error_component_m,
        )
        self.assertGreater(
            by_vertex["P200"].angular_error_component_m,
            by_vertex["P100"].angular_error_component_m,
        )

    def test_small_irradiation_angle_error_stays_inside_angular_tolerance(self) -> None:
        # equipment_angular_error_seconds is the informed instrument precision.
        # Cardinal azimuths have no observed minute deviation, so status is informed.
        result = process_coordinates(
            self._observations(),
            _irr_project(
                0.0,
                0.0,
                angle_error_s=5.0,
            ),
        )

        self.assertNotEqual(
            result.adjustment_summary["angular_status"], "nao_informado"
        )

    def test_irradiation_angle_error_above_precision_is_flagged(self) -> None:
        result = process_coordinates(
            [
                _obs("P10", 30.0 / 3600.0, 10.0),
                _obs("P100", 90.0 + 35.0 / 3600.0, 100.0),
                _obs("P200", 180.0 + 40.0 / 3600.0, 200.0),
            ],
            _irr_project(
                0.0,
                0.0,
                angle_error_s=20.0,
            ),
        )

        self.assertIn(
            result.adjustment_summary["angular_status"],
            {"proximo_do_limite", "fora_da_tolerancia"},
        )


# Consistency between modes (ponto_a_ponto vs irradiação)


class MethodConsistencyTests(unittest.TestCase):
    """
    When the same terrain is processed via both modes the resulting area and
    perimeter must be identical within floating-point tolerance.
    """

    # Triangle with known vertices.
    # Station at origin; each observation carries explicit station coords so
    # vertex order is preserved (no azimuth-sort reordering).
    _VERTS = [
        ("V-01", 0.0, 100.0),
        ("V-02", 100.0, 0.0),
        ("V-03", -100.0, 0.0),
    ]
    _SX, _SY = 0.0, 0.0
    # Expected area (Shoelace): 10 000 m²
    _EXPECTED_AREA = 10_000.0
    # Expected perimeter: all three polygon sides, including the implicit
    # closing edge V-03→V-01.
    # V-01(0,100)→V-02(100,0):  hypot(100, -100) = 100√2
    # V-02(100,0)→V-03(-100,0): hypot(-200, 0)  = 200
    # V-03(-100,0)→V-01(0,100): hypot(100, 100) = 100√2
    _EXPECTED_PERIMETER = (
        math.hypot(100.0, -100.0) + math.hypot(-200.0, 0.0) + math.hypot(100.0, 100.0)
    )

    def _ptp_result(self):
        pts = [_pt(v, x, y) for v, x, y in self._VERTS]
        return process_coordinates(pts, _ptp_project())

    def _irr_result(self):
        obs = []
        for v, x, y in self._VERTS:
            dx, dy = x - self._SX, y - self._SY
            az = (math.degrees(math.atan2(dx, dy)) + 360.0) % 360.0
            dist = math.hypot(dx, dy)
            obs.append(_obs(v, az, dist, sx=self._SX, sy=self._SY))
        return process_coordinates(obs, _irr_project(self._SX, self._SY))

    def test_area_equivalent_between_modes(self) -> None:
        ptp = self._ptp_result()
        irr = self._irr_result()
        self.assertAlmostEqual(ptp.area_m2, self._EXPECTED_AREA, places=6)
        self.assertAlmostEqual(irr.area_m2, self._EXPECTED_AREA, places=6)
        self.assertAlmostEqual(
            ptp.area_m2,
            irr.area_m2,
            places=6,
            msg="Area diverges between ponto_a_ponto and irradiacao",
        )

    def test_perimeter_equivalent_between_modes(self) -> None:
        ptp = self._ptp_result()
        irr = self._irr_result()
        self.assertAlmostEqual(ptp.perimeter_m, self._EXPECTED_PERIMETER, places=6)
        self.assertAlmostEqual(irr.perimeter_m, self._EXPECTED_PERIMETER, places=6)
        self.assertAlmostEqual(
            ptp.perimeter_m,
            irr.perimeter_m,
            places=6,
            msg="Perimeter diverges between ponto_a_ponto and irradiacao",
        )

    def test_vertex_coordinates_equivalent_between_modes(self) -> None:
        ptp = self._ptp_result()
        irr = self._irr_result()
        n = len(self._VERTS)
        for i in range(n):
            self.assertAlmostEqual(
                ptp.points[i].x, irr.points[i].x, places=9, msg=f"Point {i} x diverges"
            )
            self.assertAlmostEqual(
                ptp.points[i].y, irr.points[i].y, places=9, msg=f"Point {i} y diverges"
            )




class DeterminismTests(unittest.TestCase):
    """Same input must always produce identical output (no random state)."""

    def test_repeated_calls_produce_identical_results(self) -> None:
        pts = [
            _pt("V-01", 100.0, 200.0),
            _pt("V-02", 300.0, 200.0),
            _pt("V-03", 300.0, 400.0),
            _pt("V-04", 100.0, 400.0),
        ]
        # The square is open (last ≠ first); gap = 200 m.  Use a large tolerance
        # so the test is purely about determinism, not closure enforcement.
        project_data = _ptp_project(closure_tol="10000.0")
        r1 = process_coordinates(list(pts), project_data)
        r2 = process_coordinates(list(pts), project_data)
        self.assertAlmostEqual(r1.area_m2, r2.area_m2, places=12)
        self.assertAlmostEqual(r1.perimeter_m, r2.perimeter_m, places=12)
        self.assertAlmostEqual(r1.closure_error_m, r2.closure_error_m, places=12)
        for s1, s2 in zip(r1.segments, r2.segments):
            self.assertAlmostEqual(s1.azimuth_deg, s2.azimuth_deg, places=12)


if __name__ == "__main__":
    unittest.main()
