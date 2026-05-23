from __future__ import annotations

import math
import unittest

from app.models.schemas import CoordinatePoint, IrradiationObservation
from app.services.angles import decimal_to_dms, parse_azimuth
from app.services.geometry import (
    azimuth_to_bearing,
    build_segments,
    closure_error,
    ensure_closed,
    polygon_area,
    polygon_perimeter,
    validate_no_self_intersection,
    validate_points,
)
from app.services.irradiation import irradiation_to_points


COORD_TOLERANCE_M = 1e-8
DISTANCE_TOLERANCE_M = 1e-8
AZIMUTH_TOLERANCE_DEG = 1e-9
AREA_TOLERANCE_M2 = 1e-6


def point(vertex: str, x: float, y: float) -> CoordinatePoint:
    return CoordinatePoint(vertex=vertex, x=x, y=y)


def angular_delta(a: float, b: float) -> float:
    return abs((a - b + 180.0) % 360.0 - 180.0)


def reference_azimuth(start: CoordinatePoint, end: CoordinatePoint) -> float:
    dx = end.x - start.x
    dy = end.y - start.y
    return (math.degrees(math.atan2(dx, dy)) + 360.0) % 360.0


class TopographicPrecisionAuditTests(unittest.TestCase):
    def assertPointAlmostEqual(
        self,
        actual: CoordinatePoint,
        expected: CoordinatePoint,
        tolerance: float = COORD_TOLERANCE_M,
    ) -> None:
        self.assertAlmostEqual(actual.x, expected.x, delta=tolerance)
        self.assertAlmostEqual(actual.y, expected.y, delta=tolerance)

    def test_distances_and_azimuths_cover_axes_and_all_quadrants(self) -> None:
        base = point("O", 1000.0, 2000.0)
        cases = [
            ("N", point("N", 1000.0, 2010.0), 10.0, 0.0, "N 00°00'00\" E"),
            (
                "NE",
                point("NE", 1010.0, 2010.0),
                math.sqrt(200.0),
                45.0,
                "N 45°00'00\" E",
            ),
            ("E", point("E", 1010.0, 2000.0), 10.0, 90.0, "S 90°00'00\" E"),
            (
                "SE",
                point("SE", 1010.0, 1990.0),
                math.sqrt(200.0),
                135.0,
                "S 45°00'00\" E",
            ),
            ("S", point("S", 1000.0, 1990.0), 10.0, 180.0, "S 00°00'00\" W"),
            (
                "SW",
                point("SW", 990.0, 1990.0),
                math.sqrt(200.0),
                225.0,
                "S 45°00'00\" W",
            ),
            ("W", point("W", 990.0, 2000.0), 10.0, 270.0, "N 90°00'00\" W"),
            (
                "NW",
                point("NW", 990.0, 2010.0),
                math.sqrt(200.0),
                315.0,
                "N 45°00'00\" W",
            ),
        ]

        for label, end, expected_distance, expected_azimuth, expected_bearing in cases:
            with self.subTest(label=label):
                segment = build_segments([base, end])[0]
                self.assertAlmostEqual(
                    segment.distance_m,
                    expected_distance,
                    delta=DISTANCE_TOLERANCE_M,
                )
                self.assertLessEqual(
                    angular_delta(segment.azimuth_deg, expected_azimuth),
                    AZIMUTH_TOLERANCE_DEG,
                )
                self.assertEqual(segment.bearing, expected_bearing)
                self.assertEqual(segment.azimuth_deg, reference_azimuth(base, end))

    def test_decimal_dms_conversion_round_trips_within_half_second(self) -> None:
        cases = [
            0.0,
            12.5,
            89.9997222222,
            123.7583333333,
            180.0,
            270.25,
            359.9997222222,
        ]

        for angle in cases:
            with self.subTest(angle=angle):
                dms = decimal_to_dms(angle)
                parsed = parse_azimuth(dms)
                self.assertLessEqual(angular_delta(parsed, angle), 0.5 / 3600.0)

        self.assertAlmostEqual(parse_azimuth("12°30'15\""), 12.5041666667, places=10)
        self.assertAlmostEqual(parse_azimuth("12 30 15"), 12.5041666667, places=10)
        self.assertAlmostEqual(parse_azimuth("12:30:15"), 12.5041666667, places=10)
        self.assertAlmostEqual(parse_azimuth("359,5"), 359.5, places=10)

    def test_irradiation_generates_expected_coordinates_for_cardinal_directions(
        self,
    ) -> None:
        observations = [
            IrradiationObservation(vertex="N", azimuth_deg=0.0, distance_m=25.0),
            IrradiationObservation(vertex="E", azimuth_deg=90.0, distance_m=25.0),
            IrradiationObservation(vertex="S", azimuth_deg=180.0, distance_m=25.0),
            IrradiationObservation(vertex="W", azimuth_deg=270.0, distance_m=25.0),
        ]

        generated = irradiation_to_points(
            observations, origin_x=500000.0, origin_y=9000000.0
        )

        expected = [
            point("N", 500000.0, 9000025.0),
            point("E", 500025.0, 9000000.0),
            point("S", 500000.0, 8999975.0),
            point("W", 499975.0, 9000000.0),
        ]
        for actual, reference in zip(generated, expected, strict=True):
            self.assertPointAlmostEqual(actual, reference)

    def test_required_irradiation_cardinal_directions_from_origin(self) -> None:
        observations = [
            IrradiationObservation(vertex="P0", azimuth_deg=0.0, distance_m=10.0),
            IrradiationObservation(vertex="P90", azimuth_deg=90.0, distance_m=10.0),
            IrradiationObservation(vertex="P180", azimuth_deg=180.0, distance_m=10.0),
            IrradiationObservation(vertex="P270", azimuth_deg=270.0, distance_m=10.0),
        ]

        generated = irradiation_to_points(observations, origin_x=0.0, origin_y=0.0)
        expected = [
            point("P0", 0.0, 10.0),
            point("P90", 10.0, 0.0),
            point("P180", 0.0, -10.0),
            point("P270", -10.0, 0.0),
        ]

        for actual, reference in zip(generated, expected, strict=True):
            self.assertLess(abs(actual.x - reference.x), 0.000001)
            self.assertLess(abs(actual.y - reference.y), 0.000001)

    def test_point_to_point_and_irradiation_are_consistent_for_complex_polygon(
        self,
    ) -> None:
        station_x = 300000.0
        station_y = 7400000.0
        observations = [
            IrradiationObservation(vertex="V01", azimuth_deg=12.25, distance_m=145.123),
            IrradiationObservation(vertex="V02", azimuth_deg=77.75, distance_m=210.456),
            IrradiationObservation(vertex="V03", azimuth_deg=141.5, distance_m=188.321),
            IrradiationObservation(
                vertex="V04", azimuth_deg=214.125, distance_m=172.654
            ),
            IrradiationObservation(
                vertex="V05", azimuth_deg=289.875, distance_m=199.987
            ),
        ]
        direct_points = irradiation_to_points(
            observations, origin_x=station_x, origin_y=station_y
        )

        rebuilt_observations = []
        for p in direct_points:
            dx = p.x - station_x
            dy = p.y - station_y
            rebuilt_observations.append(
                IrradiationObservation(
                    vertex=p.vertex,
                    azimuth_deg=(math.degrees(math.atan2(dx, dy)) + 360.0) % 360.0,
                    distance_m=math.hypot(dx, dy),
                )
            )

        irradiated_points = irradiation_to_points(
            rebuilt_observations,
            origin_x=station_x,
            origin_y=station_y,
        )

        for actual, expected in zip(irradiated_points, direct_points, strict=True):
            self.assertPointAlmostEqual(actual, expected)

        direct_closed = ensure_closed(direct_points)
        irradiated_closed = ensure_closed(irradiated_points)
        self.assertAlmostEqual(
            polygon_area(irradiated_closed),
            polygon_area(direct_closed),
            delta=AREA_TOLERANCE_M2,
        )
        self.assertAlmostEqual(
            polygon_perimeter(irradiated_closed),
            polygon_perimeter(direct_closed),
            delta=DISTANCE_TOLERANCE_M,
        )

    def test_polygon_closure_and_metrics_for_simple_complex_and_large_coordinates(
        self,
    ) -> None:
        polygons = [
            (
                "simple_rectangle",
                [
                    point("A", 0.0, 0.0),
                    point("B", 100.0, 0.0),
                    point("C", 100.0, 50.0),
                    point("D", 0.0, 50.0),
                ],
                5000.0,
                300.0,
            ),
            (
                "complex_concave",
                [
                    point("A", 0.0, 0.0),
                    point("B", 80.0, 10.0),
                    point("C", 120.0, 70.0),
                    point("D", 65.0, 45.0),
                    point("E", 25.0, 95.0),
                    point("F", -20.0, 45.0),
                ],
                6662.5,
                393.6924844789157,
            ),
            (
                "large_utm_coordinates",
                [
                    point("A", 500000.123, 9000000.456),
                    point("B", 500250.789, 9000025.012),
                    point("C", 500225.333, 9000300.999),
                    point("D", 499950.654, 9000275.321),
                    point("E", 499925.111, 9000050.222),
                ],
                82365.9311605176,
                1121.4638365016913,
            ),
        ]

        for label, points, expected_area, expected_perimeter in polygons:
            with self.subTest(label=label):
                validate_points(points)
                closed = ensure_closed(points)
                validate_no_self_intersection(closed)
                self.assertAlmostEqual(
                    closure_error(closed), 0.0, delta=COORD_TOLERANCE_M
                )
                self.assertAlmostEqual(
                    polygon_area(closed), expected_area, delta=AREA_TOLERANCE_M2
                )
                self.assertAlmostEqual(
                    polygon_perimeter(closed),
                    expected_perimeter,
                    delta=DISTANCE_TOLERANCE_M,
                )

    def test_invalid_duplicate_non_finite_and_inverted_order_geometries_are_rejected(
        self,
    ) -> None:
        with self.assertRaisesRegex(ValueError, "duplicadas"):
            validate_points(
                [
                    point("A", 0.0, 0.0),
                    point("B", 10.0, 0.0),
                    point("C", 10.0, 0.0),
                    point("D", 0.0, 10.0),
                ]
            )

        with self.assertRaisesRegex(ValueError, "numericos e finitos"):
            validate_points(
                [
                    point("A", 0.0, 0.0),
                    point("B", math.inf, 0.0),
                    point("C", 0.0, 10.0),
                ]
            )

        inverted_order = ensure_closed(
            [
                point("A", 0.0, 0.0),
                point("B", 10.0, 10.0),
                point("C", 0.0, 10.0),
                point("D", 10.0, 0.0),
            ]
        )
        with self.assertRaisesRegex(ValueError, "auto-intersecao"):
            validate_no_self_intersection(inverted_order)

    def test_invalid_irradiation_numeric_values_are_rejected(self) -> None:
        valid = [
            IrradiationObservation(vertex="A", azimuth_deg=0.0, distance_m=10.0),
            IrradiationObservation(vertex="B", azimuth_deg=90.0, distance_m=10.0),
            IrradiationObservation(vertex="C", azimuth_deg=180.0, distance_m=10.0),
        ]

        with self.assertRaisesRegex(ValueError, "distancia"):
            irradiation_to_points(
                [
                    IrradiationObservation(
                        vertex="A", azimuth_deg=0.0, distance_m=float("nan")
                    ),
                    valid[1],
                    valid[2],
                ],
                origin_x=0.0,
                origin_y=0.0,
            )

        with self.assertRaisesRegex(ValueError, "azimute"):
            irradiation_to_points(
                [
                    valid[0],
                    IrradiationObservation(
                        vertex="B", azimuth_deg=float("nan"), distance_m=10.0
                    ),
                    valid[2],
                ],
                origin_x=0.0,
                origin_y=0.0,
            )

    def test_long_point_sequence_has_bounded_round_trip_accumulated_error(self) -> None:
        origin_x = 700000.0
        origin_y = 8100000.0
        observations = [
            IrradiationObservation(
                vertex=f"P{i:03d}",
                azimuth_deg=(i * 137.50776405) % 360.0,
                distance_m=50.0 + (i % 37) * 3.125,
            )
            for i in range(1, 721)
        ]
        points = irradiation_to_points(
            observations, origin_x=origin_x, origin_y=origin_y
        )
        points_by_vertex = {p.vertex: p for p in points}

        max_coordinate_error = 0.0
        max_distance_error = 0.0
        max_azimuth_error = 0.0
        for obs in observations:
            generated = points_by_vertex[obs.vertex]
            dx = generated.x - origin_x
            dy = generated.y - origin_y
            rebuilt_distance = math.hypot(dx, dy)
            rebuilt_azimuth = (math.degrees(math.atan2(dx, dy)) + 360.0) % 360.0
            expected_x = origin_x + obs.distance_m * math.sin(
                math.radians(obs.azimuth_deg)
            )
            expected_y = origin_y + obs.distance_m * math.cos(
                math.radians(obs.azimuth_deg)
            )
            max_coordinate_error = max(
                max_coordinate_error,
                math.hypot(generated.x - expected_x, generated.y - expected_y),
            )
            max_distance_error = max(
                max_distance_error, abs(rebuilt_distance - obs.distance_m)
            )
            max_azimuth_error = max(
                max_azimuth_error, angular_delta(rebuilt_azimuth, obs.azimuth_deg)
            )

        self.assertLessEqual(max_coordinate_error, COORD_TOLERANCE_M)
        self.assertLessEqual(max_distance_error, DISTANCE_TOLERANCE_M)
        self.assertLessEqual(max_azimuth_error, AZIMUTH_TOLERANCE_DEG)

    def test_azimuth_to_bearing_normalizes_out_of_range_angles(self) -> None:
        self.assertEqual(azimuth_to_bearing(405.0), "N 45°00'00\" E")
        self.assertEqual(azimuth_to_bearing(-45.0), "N 45°00'00\" W")


if __name__ == "__main__":
    unittest.main()
