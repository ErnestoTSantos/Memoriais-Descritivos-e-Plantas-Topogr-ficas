from __future__ import annotations

import unittest
from pathlib import Path

from app.services.geometry import (
    build_segments,
    ensure_closed,
    polygon_area,
    polygon_perimeter,
    validate_points,
)
from app.services.parsing import parse_csv_or_txt, parse_text_coordinates

BASE_DIR = Path(__file__).resolve().parent.parent
INDEX_HTML = BASE_DIR / "app" / "templates" / "index.html"
APP_JS = BASE_DIR / "app" / "static" / "js" / "app.js"


class ValidationWorkflowTests(unittest.TestCase):
    def test_end_to_end_processing_from_csv(self) -> None:
        csv_content = (
            "vertex,x,y\n" "V-01,0,0\n" "V-02,100,0\n" "V-03,100,50\n" "V-04,0,50\n"
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
        # Unified traverse table (replaces separate irradiation textarea)
        self.assertIn('id="traverse-body"', html)
        self.assertIn('id="traverse-table"', html)
        self.assertIn('id="station-names-list"', html)
        self.assertIn('id="initial-azimuth-dms"', html)
        self.assertIn('class="dms-group"', html)
        self.assertIn('name="measurement_mode"', html)
        self.assertIn('name="irradiation_origin_x"', html)
        self.assertIn('name="irradiation_origin_y"', html)
        self.assertIn('name="equipment_angular_error_seconds"', html)
        self.assertIn('type="number"', html)
        self.assertIn('inputmode="decimal"', html)
        self.assertIn('id="map"', html)
        self.assertIn('data-format="pdf"', html)
        self.assertIn('data-format="docx"', html)
        self.assertIn('data-format="dxf"', html)
        self.assertIn('data-format="dwg"', html)
        self.assertIn('id="points-adjustment-body"', html)
        self.assertIn('id="planimetric-summary"', html)
        self.assertIn("Tabela Planimétrica Completa", html)
        for header in (
            "Estação",
            "Ponto inicial",
            "Ponto final",
            "Ângulo obs.",
            "Ajuste angular",
            "Ângulo corr.",
            "E(+)",
            "W(-)",
            "N(+)",
            "S(-)",
            "Erro X",
            "Erro Y",
            "X acum.",
            "Y acum.",
        ):
            self.assertIn(header, html)

    def test_irradiation_station_ui_uses_registered_station_names(self) -> None:
        js = APP_JS.read_text(encoding="utf-8")

        self.assertIn('list="station-names-list"', js)
        self.assertIn('n === 1 ? "1 estação" : `${n} estações`', js)
        self.assertIn("function updateStationNameOptions()", js)
        self.assertIn("observations && names.size > 0", js)

    def test_frontend_renders_global_tolerance_diagnostics(self) -> None:
        js = APP_JS.read_text(encoding="utf-8")

        self.assertIn("adjustment_summary", js)
        self.assertIn("accumulated_error_m", js)
        self.assertIn("contribution_status", js)
        self.assertIn("correction_e_m", js)
        self.assertIn("points-adjustment", js)
        self.assertIn("planimetric_table", js)
        self.assertIn("getPlanimetricRows", js)
        for field in (
            "observed_angle",
            "angular_adjustment",
            "corrected_angle",
            "east_positive",
            "west_negative",
            "north_positive",
            "south_negative",
            "accumulated_x",
            "accumulated_y",
            "error_contribution_percent",
        ):
            self.assertIn(field, js)

    def test_text_parser_supports_task_flow(self) -> None:
        text = "V-01, 0, 0\nV-02, 30, 0\nV-03, 30, 40"
        points = parse_text_coordinates(text)
        validate_points(points)
        self.assertEqual(len(points), 3)


if __name__ == "__main__":
    unittest.main()
