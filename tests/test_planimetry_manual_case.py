from __future__ import annotations

import unittest

from app.services.angles import parse_azimuth
from app.services.planimetry import (
    PlanimetryLeg,
    compute_planimetry_traverse,
)


def _deg(dms: str) -> float:
    return parse_azimuth(dms)


def _angular_delta_seconds(actual: float, expected: float) -> float:
    delta_deg = abs((actual - expected + 180.0) % 360.0 - 180.0)
    return delta_deg * 3600.0


def _bearing_angle_and_quadrant(value: str) -> tuple[float, str]:
    angle_text, quadrant = value.rsplit(" ", maxsplit=1)
    return parse_azimuth(angle_text), quadrant


class ManualPlanimetryValidationTests(unittest.TestCase):
    """
    Real validation case transcribed from the field notebook.

    The notebook line for D-A appears as 18.946 m in one place, but the
    expected perimeter (74.035 m) and the D-A projection N=18.659 m are only
    compatible with 18.962 m. The fixture keeps the coherent manual value so
    the automated test validates the calculation instead of preserving that
    transcription conflict.
    """

    def setUp(self) -> None:
        self.result = compute_planimetry_traverse(
            [
                PlanimetryLeg("A", "B", 12.391, _deg("102°16'31\"")),
                PlanimetryLeg("B", "C", 25.023, _deg("89°36'19\"")),
                PlanimetryLeg("C", "D", 17.659, _deg("65°40'58\"")),
                PlanimetryLeg("D", "A", 18.962, _deg("102°26'14\"")),
            ],
            initial_azimuth_deg=_deg("292°30'54\""),
        )

    def test_calculates_azimuths_and_bearings_from_adjusted_angles(self) -> None:
        self.assertAlmostEqual(self.result.angular_misclosure_seconds, 2.0, delta=1e-6)
        self.assertAlmostEqual(
            self.result.applied_angle_correction_seconds, -0.5, delta=1e-6
        )

        expected = [
            ("292°30'54\"", "67°29'06\" NW"),
            ("22°07'13\"", "22°07'13\" NE"),
            ("87°48'09\"", "87°48'09\" NE"),
            ("190°14'23\"", "10°14'23\" SW"),
        ]

        for segment, (expected_azimuth, expected_bearing) in zip(
            self.result.segments, expected, strict=True
        ):
            with self.subTest(segment=f"{segment.start_vertex}-{segment.end_vertex}"):
                self.assertLessEqual(
                    _angular_delta_seconds(
                        segment.azimuth_deg, parse_azimuth(expected_azimuth)
                    ),
                    1.000001,
                )

                actual_bearing_angle, actual_quadrant = _bearing_angle_and_quadrant(
                    segment.bearing
                )
                expected_bearing_angle, expected_quadrant = _bearing_angle_and_quadrant(
                    expected_bearing
                )
                self.assertEqual(actual_quadrant, expected_quadrant)
                self.assertLessEqual(
                    _angular_delta_seconds(
                        actual_bearing_angle, expected_bearing_angle
                    ),
                    1.000001,
                )

    def test_calculates_reported_projection_components(self) -> None:
        expected_reported_projection = [
            (-11.446, 4.745),
            (9.422, 23.181),
            (17.646, 0.677),
            (-3.371, -18.659),
        ]

        for segment, (expected_e, expected_n) in zip(
            self.result.segments, expected_reported_projection, strict=True
        ):
            with self.subTest(segment=f"{segment.start_vertex}-{segment.end_vertex}"):
                self.assertAlmostEqual(
                    segment.reported_delta_e_m, expected_e, delta=0.01
                )
                self.assertAlmostEqual(
                    segment.reported_delta_n_m, expected_n, delta=0.01
                )

    def test_distributes_closure_and_calculates_adjusted_area(self) -> None:
        expected_correction_e = [0.025, 0.050, 0.036, 0.038]

        self.assertGreater(
            self.result.reported_closure_error_m,
            15.0,
            "The azimuth/projection signs in the notebook do not form the adjusted traverse.",
        )
        self.assertEqual(
            [segment.projection_direction_reversed for segment in self.result.segments],
            [False, True, False, True],
        )
        self.assertLess(self.result.closure_error_m, 1.0)

        for segment, expected_e in zip(
            self.result.segments, expected_correction_e, strict=True
        ):
            with self.subTest(segment=f"{segment.start_vertex}-{segment.end_vertex}"):
                self.assertAlmostEqual(segment.correction_e_m, -expected_e, delta=0.01)

        self.assertAlmostEqual(
            sum(segment.correction_e_m for segment in self.result.segments),
            -self.result.closure_dx_m,
            delta=1e-9,
        )
        self.assertAlmostEqual(
            sum(segment.correction_n_m for segment in self.result.segments),
            -self.result.closure_dy_m,
            delta=1e-9,
        )
        self.assertAlmostEqual(self.result.adjusted_points[-1].x, 0.0, delta=1e-9)
        self.assertAlmostEqual(self.result.adjusted_points[-1].y, 0.0, delta=1e-9)
        self.assertAlmostEqual(self.result.perimeter_m, 74.035, delta=0.01)
        self.assertAlmostEqual(self.result.area_m2, 317.952, delta=0.10)


if __name__ == "__main__":
    unittest.main()
