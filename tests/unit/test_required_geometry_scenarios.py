from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import ezdxf

from app.services.geometry import (
    ensure_closed,
    polygon_area,
    polygon_perimeter,
    validate_points,
)
from app.services.parsing import (
    parse_csv_or_txt,
    parse_shapefile_zip,
    parse_text_coordinates,
)
from app.services.processing import build_project_data, process_coordinates
from app.services.reports import export_dxf, export_pdf


class RequiredGeometryScenariosTests(unittest.TestCase):
    def _project_data(self):
        return build_project_data(
            {
                "property_name": "Fazenda Boa Vista",
                "owner_name": "Maria Silva",
                "municipality": "Belem",
                "state": "PA",
                "datum": "SIRGAS2000",
                "coordinate_system": "UTM",
                "measurement_mode": "planimetrico",
            }
        )

    def test_simple_square_closes_metrics_and_generates_memorial(self) -> None:
        points = parse_text_coordinates("V-01,0,0\nV-02,10,0\nV-03,10,10\nV-04,0,10")
        result = process_coordinates(points, self._project_data())

        self.assertEqual(result.points[0].x, result.points[-1].x)
        self.assertEqual(result.points[0].y, result.points[-1].y)
        self.assertAlmostEqual(result.area_m2, 100.0, places=6)
        self.assertAlmostEqual(result.perimeter_m, 40.0, places=6)
        self.assertEqual(len(result.segments), 4)
        self.assertEqual(result.segments[-1].start_vertex, "V-04")
        self.assertEqual(result.segments[-1].end_vertex, "V-01")
        for segment in result.segments:
            self.assertAlmostEqual(segment.distance_m, 10.0, places=6)
        self.assertIn("V-01", result.memorial_text)
        self.assertIn("Area: 100.00 m2", result.memorial_text)
        self.assertIn("Perimetro: 40.00 m", result.memorial_text)

    def test_polygon_without_explicit_closure_is_closed_before_processing(self) -> None:
        points = parse_text_coordinates("A,0,0\nB,5,0\nC,5,5\nD,0,5")
        closed = ensure_closed(points)

        self.assertEqual(len(closed), 5)
        self.assertEqual(closed[-1].vertex, "A")

    def test_duplicate_coordinates_are_rejected(self) -> None:
        points = parse_text_coordinates("A,0,0\nB,10,0\nC,10,0\nD,0,10")

        with self.assertRaisesRegex(ValueError, "duplicadas"):
            validate_points(points)

    def test_self_intersecting_polygon_is_rejected(self) -> None:
        points = parse_text_coordinates("A,0,0\nB,10,10\nC,0,10\nD,10,0")

        with self.assertRaisesRegex(ValueError, "auto-intersecao"):
            process_coordinates(points, self._project_data())

    def test_invalid_csv_with_non_numeric_coordinates_reports_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "Valor inválido"):
            parse_csv_or_txt(b"vertex,x,y\nA,abc,0\nB,1,0\nC,1,1\n")

    def test_corrupted_shapefile_zip_reports_friendly_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "corrompido|ZIP invalido"):
            parse_shapefile_zip(b"not-a-zip")

    def test_memorial_has_no_empty_required_fields(self) -> None:
        result = process_coordinates(
            parse_text_coordinates("A,0,0\nB,8,0\nC,8,4\nD,0,4"),
            self._project_data(),
        )

        for marker in [
            "Proprietario:",
            "Municipio/UF:",
            "Sistema Geodesico:",
            "Sistema de Coordenadas:",
        ]:
            line = next(
                line
                for line in result.memorial_text.splitlines()
                if line.startswith(marker)
            )
            self.assertGreater(len(line.split(":", maxsplit=1)[1].strip()), 0)

    def test_pdf_export_opens_and_has_rendered_content(self) -> None:
        result = process_coordinates(
            parse_text_coordinates("A,0,0\nB,8,0\nC,8,4\nD,0,4"),
            self._project_data(),
        )

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "memorial.pdf"
            export_pdf(path, "Memorial", result.memorial_text, result.points[:-1])
            content = path.read_bytes()

        self.assertTrue(content.startswith(b"%PDF"))
        self.assertGreater(len(content), 1000)

    def test_dxf_export_is_readable_and_contains_autocad_entities(self) -> None:
        points = parse_text_coordinates("A,0,0\nB,8,0\nC,8,4\nD,0,4")

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "planta.dxf"
            export_dxf(path, points, "Planta")
            doc = ezdxf.readfile(path)

        modelspace = doc.modelspace()
        self.assertEqual(len(modelspace.query("LWPOLYLINE")), 1)
        self.assertEqual(len(modelspace.query("CIRCLE")), 4)

    def test_square_area_and_perimeter_helpers_are_positive_and_correct(self) -> None:
        closed = ensure_closed(parse_text_coordinates("A,0,0\nB,10,0\nC,10,10\nD,0,10"))

        self.assertGreater(polygon_area(closed), 0)
        self.assertAlmostEqual(polygon_perimeter(closed), 40.0, places=6)


if __name__ == "__main__":
    unittest.main()
