from __future__ import annotations

import unittest
from pathlib import Path

from app.services.geometry import build_segments, ensure_closed, polygon_area, polygon_perimeter, validate_points
from app.services.parsing import parse_csv_or_txt, parse_text_coordinates

BASE_DIR = Path(__file__).resolve().parent.parent
INDEX_HTML = BASE_DIR / "app" / "templates" / "index.html"


class ValidationWorkflowTests(unittest.TestCase):
    def test_end_to_end_processing_from_csv(self) -> None:
        csv_content = (
            "vertex,x,y\n"
            "V-01,0,0\n"
            "V-02,100,0\n"
            "V-03,100,50\n"
            "V-04,0,50\n"
        ).encode("utf-8")

        points = parse_csv_or_txt(csv_content)
        validate_points(points)
        closed = ensure_closed(points)
        segments = build_segments(closed)

        self.assertEqual(len(segments), 4)
        self.assertAlmostEqual(polygon_area(closed), 5000.0, places=6)
        self.assertAlmostEqual(polygon_perimeter(closed), 300.0, places=6)

    def test_ui_contains_required_main_actions(self) -> None:
        html = INDEX_HTML.read_text(encoding="utf-8")
        self.assertIn('id="process-form"', html)
        self.assertIn('name="coordinates_text"', html)
        self.assertIn('name="measurement_mode"', html)
        self.assertIn('name="irradiation_origin_x"', html)
        self.assertIn('name="irradiation_origin_y"', html)
        self.assertIn('name="irradiation_angle_error_seconds"', html)
        self.assertIn('name="angle_error_limit_seconds"', html)
        self.assertIn('type="number"', html)
        self.assertIn('inputmode="decimal"', html)
        self.assertIn('id="map"', html)
        self.assertIn('data-format="pdf"', html)
        self.assertIn('data-format="docx"', html)
        self.assertIn('data-format="dxf"', html)
        self.assertIn('data-format="dwg"', html)

    def test_text_parser_supports_task_flow(self) -> None:
        text = "V-01, 0, 0\nV-02, 30, 0\nV-03, 30, 40"
        points = parse_text_coordinates(text)
        validate_points(points)
        self.assertEqual(len(points), 3)


if __name__ == "__main__":
    unittest.main()
