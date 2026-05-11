from __future__ import annotations

import unittest

from app.services.processing import build_project_data


class ProcessingBlankFieldsTests(unittest.TestCase):
    def test_build_project_data_accepts_blank_optional_numeric_fields(self) -> None:
        project_data = build_project_data(
            {
                "measurement_mode": "ponto_a_ponto",
                "irradiation_angle_error_seconds": "",
                "angle_error_limit_seconds": "   ",
                "closure_tolerance_m": "",
            }
        )

        self.assertIsNone(project_data.irradiation_angle_error_seconds)
        self.assertIsNone(project_data.angle_error_limit_seconds)
        self.assertAlmostEqual(project_data.closure_tolerance_m or 0.0, 0.05, places=6)


if __name__ == "__main__":
    unittest.main()
