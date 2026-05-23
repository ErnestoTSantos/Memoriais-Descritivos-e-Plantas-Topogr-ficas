from __future__ import annotations

import unittest

from app.services.processing import build_project_data


class ProcessingBlankFieldsTests(unittest.TestCase):
    def test_build_project_data_accepts_blank_optional_numeric_fields(self) -> None:
        project_data = build_project_data(
            {
                "measurement_mode": "planimetrico",
                "equipment_angular_error_seconds": "",
            }
        )

        self.assertIsNone(project_data.equipment_angular_error_seconds)


if __name__ == "__main__":
    unittest.main()
