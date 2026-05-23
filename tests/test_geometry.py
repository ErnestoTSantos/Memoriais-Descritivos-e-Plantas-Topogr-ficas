from __future__ import annotations

import unittest

from app.services.geometry import (
    build_segments,
    closure_error,
    ensure_closed,
    polygon_area,
    polygon_perimeter,
    validate_no_self_intersection,
    validate_points,
)
from app.services.parsing import parse_text_coordinates


class GeometryServiceTests(unittest.TestCase):
    def test_rectangle_metrics_are_exact(self) -> None:
        points = parse_text_coordinates(
            "V-01, 0, 0\nV-02, 100, 0\nV-03, 100, 50\nV-04, 0, 50"
        )
        validate_points(points)
        closed = ensure_closed(points)

        self.assertAlmostEqual(polygon_area(closed), 5000.0, places=6)
        self.assertAlmostEqual(polygon_perimeter(closed), 300.0, places=6)
        self.assertAlmostEqual(closure_error(closed), 0.0, places=6)
        segments = build_segments(closed)
        self.assertEqual(len(segments), 4)
        self.assertEqual(segments[0].azimuth_dms, "090°00'00\"")

    def test_requires_minimum_three_unique_points(self) -> None:
        points = parse_text_coordinates("V-01, 0, 0\nV-02, 1, 1\nV-03, 1, 1")
        with self.assertRaises(ValueError):
            validate_points(points)

    def test_rejects_self_intersecting_polygon(self) -> None:
        points = parse_text_coordinates(
            "V-01, 0, 0\nV-02, 2, 2\nV-03, 0, 2\nV-04, 2, 0"
        )
        closed = ensure_closed(points)

        with self.assertRaisesRegex(ValueError, "auto-intersecao"):
            validate_no_self_intersection(closed)


if __name__ == "__main__":
    unittest.main()
