from __future__ import annotations

import json
import os
import unittest


@unittest.skipUnless(
    os.getenv("DJANGO_SETTINGS_MODULE"),
    "Django integration tests require manage.py test.",
)
class ApiRestFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        from django.test import Client

        self.client = Client()
        self.payload = {
            "property_name": "Fazenda Boa Vista",
            "owner_name": "Maria Silva",
            "municipality": "Belem",
            "state": "PA",
            "datum": "SIRGAS2000",
            "coordinate_system": "UTM",
            "measurement_mode": "planimetrico",
            "coordinates_text": "A,0,0\nB,10,0\nC,10,10\nD,0,10",
        }

    def test_process_api_serializes_successful_polygon(self) -> None:
        response = self.client.post("/api/process", data=self.payload)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["measurement_mode"], "planimetrico")
        self.assertEqual(len(data["segments"]), 4)
        self.assertAlmostEqual(data["area_m2"], 100.0, places=6)
        self.assertIn("memorial_text", data)
        self.assertIn("adjustment_summary", data)
        self.assertIn("accumulated_error_m", data["adjustment_summary"])
        self.assertIn("tolerance_m", data["adjustment_summary"])
        self.assertIn("correction_e_m", data["segments"][0])
        self.assertIn("planimetric_table", data)
        self.assertIn("planimetric_segments", data)
        self.assertIn("observed_angle", data["segments"][0])
        self.assertIn("east_positive", data["segments"][0])
        self.assertIn("accumulated_x", data["segments"][0])
        self.assertIn("formulas", data["planimetric_table"])
        from core.models import ProcessRun

        run = ProcessRun.objects.latest("id")
        self.assertIn("segments", run.planimetric_table)
        self.assertIn("formulas", run.planimetric_table)

    def test_process_api_rejects_invalid_payload(self) -> None:
        bad_payload = {**self.payload, "coordinates_text": "A,0,0\nB,10,0\nC,10,0"}
        response = self.client.post("/api/process", data=bad_payload)

        self.assertEqual(response.status_code, 400)
        self.assertIn("detail", response.json())

    def test_export_pdf_api_returns_file_response(self) -> None:
        points = [
            {"vertex": "A", "x": 0, "y": 0},
            {"vertex": "B", "x": 10, "y": 0},
            {"vertex": "C", "x": 10, "y": 10},
            {"vertex": "D", "x": 0, "y": 10},
        ]
        response = self.client.post(
            "/api/export/pdf",
            data=json.dumps({**self.payload, "points": points}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")


if __name__ == "__main__":
    unittest.main()
