from __future__ import annotations

import unittest

from app.services.parsing import parse_text_coordinates
from app.services.processing import build_project_data, process_coordinates


class ProcessingServiceTests(unittest.TestCase):
    def test_build_project_data_rejects_non_positive_angle_limit(self) -> None:
        with self.assertRaisesRegex(ValueError, "limite do erro angular"):
            build_project_data({"angle_error_limit_seconds": "0"})

    def test_build_project_data_rejects_angle_error_above_limit(self) -> None:
        with self.assertRaisesRegex(ValueError, "excede o limite"):
            build_project_data(
                {
                    "measurement_mode": "ponto_a_ponto",
                    "irradiation_angle_error_seconds": "31",
                    "angle_error_limit_seconds": "30",
                }
            )

    def test_process_coordinates_applies_angle_adjustment_to_point_to_point(self) -> None:
        points = parse_text_coordinates("V-01, 0, 0\nV-02, 10, 0\nV-03, 10, 10")
        project_data = build_project_data(
            {
                "measurement_mode": "ponto_a_ponto",
                "irradiation_angle_error_seconds": "30",
                "angle_error_limit_seconds": "60",
            }
        )

        result = process_coordinates(points, project_data)
        self.assertEqual(len(result.segments), 3)
        self.assertAlmostEqual(result.segments[0].applied_angle_error_seconds, 30.0, places=6)


if __name__ == "__main__":
    unittest.main()
