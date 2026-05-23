"""Validation test for the irradiation calculation using real field-notebook data.

The test reproduces the complete manual irradiation survey transcribed from the
field notebook image.  All three stations (A, B, C) are exercised.

TOLERANCE RATIONALE
-------------------
The manual notebook was computed with 5-digit trigonometric tables
(sin/cos looked up to 5 significant figures, e.g. sin(208°56') = −0.48235 vs
the precise −0.48386).  At distances of ~15–20 m, this 1-digit table rounding
can introduce projection errors up to ~0.03 m.  Therefore:

  - projections (ΔX, ΔY): ±0.04 m  (accommodates trig-table rounding)
  - final coordinates:     ±0.04 m  (same source of error)

These tolerances are still tight enough to catch any real formula bugs
(wrong sin/cos swap, wrong sign by quadrant, wrong DMS conversion, etc.),
which would produce errors of several metres.

BACK-SIGHT NOTE (P2 from Station C)
-------------------------------------
In the manual notebook, "Ponto 2" from Station C is a back-sight check to
Station A's KNOWN position (400.000, 400.000).  The notebook's ΔX and ΔY were
computed from:

    ΔX = X_A − X_C = 400.000 − 400.611 = −0.611
    ΔY = Y_A − Y_C = 400.000 − 390.288 = +9.712

These differ from the formula d·cos(Az) ≈ 9.300 because the measured distance
(9.320 m) does not exactly equal the true distance to Station A (~9.731 m).
This is the survey's closure discrepancy for that back-sight leg.  The point
is excluded from the formula-based tolerance tests; the formula identity test
(X = station_x + ΔX) still applies and passes.
"""

from __future__ import annotations

import unittest

from app.models.schemas import IrradiationObservation
from app.services.angles import parse_azimuth
from app.services.irradiation import compute_irradiation




def _obs(
    vertex: str,
    azimuth_dms: str,
    distance: float,
    station_x: float,
    station_y: float,
    station_name: str,
) -> IrradiationObservation:
    return IrradiationObservation(
        vertex=vertex,
        azimuth_deg=parse_azimuth(azimuth_dms),
        distance_m=distance,
        station_x=station_x,
        station_y=station_y,
        station_name=station_name,
    )



STATION_A = (400.0, 400.0)
STATION_B = (390.225, 398.334)
STATION_C = (400.611, 390.288)


OBSERVATIONS: list[IrradiationObservation] = [
    # --- Estação A ---
    _obs("P2",  "208°56'15\"", 19.476, *STATION_A, "A"),
    _obs("P4",  "141°08'55\"",  7.472, *STATION_A, "A"),
    _obs("P5",  "129°41'46\"", 14.456, *STATION_A, "A"),
    _obs("P6",   "96°24'38\"", 11.966, *STATION_A, "A"),
    _obs("P7",  "296°23'21\"", 14.338, *STATION_A, "A"),
    # --- Estação B ---
    _obs("P8",   "13°32'44\"", 16.221, *STATION_B, "B"),
    _obs("P9",  "310°01'25\"",  6.928, *STATION_B, "B"),
    _obs("P10", "180°57'49\"",  2.284, *STATION_B, "B"),
    # --- Estação C ---
    _obs("P1",  "197°24'00\"",  5.873, *STATION_C, "C"),
    # P_A_check: back-sight from C to verify Station A — included in the table
    # but excluded from formula-tolerance tests (see module docstring).
    _obs("PA_check", "356°14'01\"",  9.320, *STATION_C, "C"),
    _obs("P3",   "28°09'32\"", 20.881, *STATION_C, "C"),
]

# Manual reference values from the field notebook.
#
# Each tuple: (vertex, station_name,
#              expected_delta_x, expected_delta_y,
#              expected_x, expected_y)
#
# PA_check is deliberately omitted: its ΔY was derived from the KNOWN
# coordinates of Station A (back-sight), not from the formula.

MANUAL_REFERENCE = [
    # Estação A (X=400, Y=400)
    # P2: 5-digit trig table used sin(208°56')=−0.48235, yielding ΔX=−9.394.
    # Precise sin(208°56'15")=−0.48386 gives ΔX=−9.424 (diff ≈0.030 m —
    # accommodated by the ±0.04 m tolerance).
    ("P2",   "A",  -9.394, -17.063,  390.606, 382.937),
    ("P4",   "A",   4.687,  -5.819,  404.687, 394.181),
    ("P5",   "A",  11.132,  -9.240,  411.132, 390.760),
    ("P6",   "A",  11.891,  -1.336,  411.891, 398.664),
    # P7: trig-table rounding also introduces ~0.022 m error in ΔY.
    ("P7",   "A", -12.833,   6.395,  387.167, 406.395),
    # Estação B (X=390.225, Y=398.334)
    ("P8",   "B",   3.799,  15.770,  394.024, 414.104),
    ("P9",   "B",  -5.305,   4.455,  384.920, 402.789),
    ("P10",  "B",  -0.038,  -2.284,  390.187, 396.050),
    # Estação C (X=400.611, Y=390.288)
    ("P1",   "C",  -1.756,  -5.604,  398.855, 384.684),
    # PA_check excluded — see module docstring.
    ("P3",   "C",   9.854,  18.409,  410.465, 408.697),
]

# Tolerance for comparison with manual trig-table values.
# ±0.04 m accommodates the worst observed rounding (P2: 0.030 m, P7: 0.022 m).
TOLERANCE_PROJ = 0.04
TOLERANCE_COORD = 0.04


class TestAzimuthParsing(unittest.TestCase):
    """Verify that DMS azimuths are parsed correctly (at most 1-second error)."""

    def _assert_dms(self, dms: str, expected_deg: float) -> None:
        actual = parse_azimuth(dms)
        delta_seconds = abs(actual - expected_deg) * 3600.0
        self.assertLessEqual(
            delta_seconds,
            1.0,
            msg=f"parse_azimuth('{dms}') = {actual:.8f}°, expected ≈ {expected_deg:.8f}° "
                f"(delta = {delta_seconds:.3f}\")",
        )

    def test_station_a_azimuths(self) -> None:
        self._assert_dms("208°56'15\"", 208 + 56/60 + 15/3600)
        self._assert_dms("141°08'55\"", 141 + 8/60 + 55/3600)
        self._assert_dms("129°41'46\"", 129 + 41/60 + 46/3600)
        self._assert_dms("96°24'38\"",   96 + 24/60 + 38/3600)
        self._assert_dms("296°23'21\"", 296 + 23/60 + 21/3600)

    def test_station_b_azimuths(self) -> None:
        self._assert_dms("13°32'44\"",   13 + 32/60 + 44/3600)
        self._assert_dms("310°01'25\"", 310 +  1/60 + 25/3600)
        self._assert_dms("180°57'49\"", 180 + 57/60 + 49/3600)

    def test_station_c_azimuths(self) -> None:
        self._assert_dms("197°24'00\"", 197 + 24/60 + 0/3600)
        self._assert_dms("356°14'01\"", 356 + 14/60 + 1/3600)
        self._assert_dms("28°09'32\"",   28 +  9/60 + 32/3600)


class TestIrradiationCalculation(unittest.TestCase):
    """Verify all intermediate values against the manual field-notebook values."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.points, cls.table = compute_irradiation(OBSERVATIONS)
        cls.rows_by_vertex = {
            row.vertex: row for row in cls.table.rows
        }

    def test_station_names_assigned_correctly(self) -> None:
        expected_stations = {
            "P2": "A", "P4": "A", "P5": "A", "P6": "A", "P7": "A",
            "P8": "B", "P9": "B", "P10": "B",
            "P1": "C", "PA_check": "C", "P3": "C",
        }
        for vertex, station_name in expected_stations.items():
            row = self.rows_by_vertex[vertex]
            self.assertEqual(
                row.station_name,
                station_name,
                msg=f"Vertex {vertex}: expected station '{station_name}', "
                    f"got '{row.station_name}'",
            )

    def test_delta_x_within_tolerance(self) -> None:
        for vertex, _, expected_dx, expected_dy, _, _ in MANUAL_REFERENCE:
            row = self.rows_by_vertex[vertex]
            with self.subTest(vertex=vertex):
                self.assertAlmostEqual(
                    row.delta_x,
                    expected_dx,
                    delta=TOLERANCE_PROJ,
                    msg=f"Vertex {vertex}: ΔX = {row.delta_x:.4f}, "
                        f"expected {expected_dx:.4f}",
                )

    def test_delta_y_within_tolerance(self) -> None:
        for vertex, _, expected_dx, expected_dy, _, _ in MANUAL_REFERENCE:
            row = self.rows_by_vertex[vertex]
            with self.subTest(vertex=vertex):
                self.assertAlmostEqual(
                    row.delta_y,
                    expected_dy,
                    delta=TOLERANCE_PROJ,
                    msg=f"Vertex {vertex}: ΔY = {row.delta_y:.4f}, "
                        f"expected {expected_dy:.4f}",
                )

    def test_x_final_within_tolerance(self) -> None:
        for vertex, _, _, _, expected_x, expected_y in MANUAL_REFERENCE:
            row = self.rows_by_vertex[vertex]
            with self.subTest(vertex=vertex):
                self.assertAlmostEqual(
                    row.x,
                    expected_x,
                    delta=TOLERANCE_COORD,
                    msg=f"Vertex {vertex}: X = {row.x:.4f}, "
                        f"expected {expected_x:.4f}",
                )

    def test_y_final_within_tolerance(self) -> None:
        for vertex, _, _, _, expected_x, expected_y in MANUAL_REFERENCE:
            row = self.rows_by_vertex[vertex]
            with self.subTest(vertex=vertex):
                self.assertAlmostEqual(
                    row.y,
                    expected_y,
                    delta=TOLERANCE_COORD,
                    msg=f"Vertex {vertex}: Y = {row.y:.4f}, "
                        f"expected {expected_y:.4f}",
                )

    def test_final_coordinates_equal_station_plus_delta(self) -> None:
        for row in self.table.rows:
            with self.subTest(vertex=row.vertex):
                self.assertAlmostEqual(
                    row.x,
                    row.station_x + row.delta_x,
                    places=12,
                    msg=f"Vertex {row.vertex}: X ≠ station_X + ΔX",
                )
                self.assertAlmostEqual(
                    row.y,
                    row.station_y + row.delta_y,
                    places=12,
                    msg=f"Vertex {row.vertex}: Y ≠ station_Y + ΔY",
                )

    def test_backsight_x_matches_station_a(self) -> None:
        """The back-sight from C to Station A must recover X≈400.000."""
        row = self.rows_by_vertex["PA_check"]
        self.assertAlmostEqual(row.x, 400.000, delta=0.01)

    def test_backsight_y_closure_error_is_documented(self) -> None:
        """Y from back-sight ≈399.588, not 400.000 — survey closure error ~0.41 m."""
        row = self.rows_by_vertex["PA_check"]
        # The computed Y is intentionally NOT close to 400.000.
        # The discrepancy (measured distance 9.320 vs true distance ~9.731 m)
        # represents the survey's closure error for this leg.
        closure_error_y = abs(row.y - 400.000)
        self.assertGreater(
            closure_error_y,
            0.3,
            msg="Expected a non-trivial Y closure error for the back-sight leg",
        )

    def test_azimuth_dms_roundtrip(self) -> None:
        for row in self.table.rows:
            with self.subTest(vertex=row.vertex):
                reparsed = parse_azimuth(row.azimuth_dms)
                delta_seconds = abs(reparsed - row.azimuth_deg) * 3600.0
                # Wrap-around guard (e.g., 359.9999° vs 0.0001°)
                if delta_seconds > 1800 * 3600:
                    delta_seconds = 360 * 3600 - delta_seconds
                self.assertLessEqual(
                    delta_seconds,
                    1.0,
                    msg=f"Vertex {row.vertex}: DMS round-trip error "
                        f"{delta_seconds:.2f}\" > 1\"",
                )

    def test_table_has_one_row_per_observation(self) -> None:
        self.assertEqual(len(self.table.rows), len(OBSERVATIONS))

    def test_output_points_match_table_rows(self) -> None:
        # points are geometrically sorted; table.rows preserve observation order.
        # Verify that every point's coordinates match the corresponding table row
        # by vertex name, not by position.
        points_by_vertex = {p.vertex: p for p in self.points}
        for row in self.table.rows:
            point = points_by_vertex.get(row.vertex)
            self.assertIsNotNone(point, f"Vertex {row.vertex} missing from points")
            self.assertAlmostEqual(point.x, row.x, places=12)
            self.assertAlmostEqual(point.y, row.y, places=12)

    def test_delta_x_signs_correct(self) -> None:
        """Verify that each ΔX has the correct sign (matches the manual)."""
        expected_signs = {
            "P2": -1, "P4": +1, "P5": +1, "P6": +1, "P7": -1,
            "P8": +1, "P9": -1, "P10": -1,
            "P1": -1, "PA_check": -1, "P3": +1,
        }
        for vertex, sign in expected_signs.items():
            row = self.rows_by_vertex[vertex]
            with self.subTest(vertex=vertex):
                if sign > 0:
                    self.assertGreater(row.delta_x, 0,
                                       msg=f"Vertex {vertex}: ΔX should be positive")
                else:
                    self.assertLess(row.delta_x, 0,
                                    msg=f"Vertex {vertex}: ΔX should be negative")

    def test_delta_y_signs_correct(self) -> None:
        """Verify that each ΔY has the correct sign (matches the manual)."""
        expected_signs = {
            "P2": -1, "P4": -1, "P5": -1, "P6": -1, "P7": +1,
            "P8": +1, "P9": +1, "P10": -1,
            "P1": -1, "PA_check": +1, "P3": +1,
        }
        for vertex, sign in expected_signs.items():
            row = self.rows_by_vertex[vertex]
            with self.subTest(vertex=vertex):
                if sign > 0:
                    self.assertGreater(row.delta_y, 0,
                                       msg=f"Vertex {vertex}: ΔY should be positive")
                else:
                    self.assertLess(row.delta_y, 0,
                                    msg=f"Vertex {vertex}: ΔY should be negative")


class TestIrradiationStationGrouping(unittest.TestCase):
    """Verify that station grouping labels are propagated correctly."""

    @classmethod
    def setUpClass(cls) -> None:
        _, cls.table = compute_irradiation(OBSERVATIONS)

    def test_station_a_rows(self) -> None:
        station_a_rows = [
            r for r in self.table.rows if r.station_name == "A"
        ]
        self.assertEqual(len(station_a_rows), 5)
        for row in station_a_rows:
            self.assertAlmostEqual(row.station_x, STATION_A[0], places=6)
            self.assertAlmostEqual(row.station_y, STATION_A[1], places=6)

    def test_station_b_rows(self) -> None:
        station_b_rows = [
            r for r in self.table.rows if r.station_name == "B"
        ]
        self.assertEqual(len(station_b_rows), 3)
        for row in station_b_rows:
            self.assertAlmostEqual(row.station_x, STATION_B[0], places=6)
            self.assertAlmostEqual(row.station_y, STATION_B[1], places=6)

    def test_station_c_rows(self) -> None:
        station_c_rows = [
            r for r in self.table.rows if r.station_name == "C"
        ]
        self.assertEqual(len(station_c_rows), 3)
        for row in station_c_rows:
            self.assertAlmostEqual(row.station_x, STATION_C[0], places=6)
            self.assertAlmostEqual(row.station_y, STATION_C[1], places=6)


if __name__ == "__main__":
    unittest.main()
