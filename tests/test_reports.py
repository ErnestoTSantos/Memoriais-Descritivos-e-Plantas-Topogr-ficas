from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.services.geometry import build_segments, ensure_closed
from app.services.parsing import parse_text_coordinates
from app.services.reports import export_docx, export_dxf, export_pdf, generate_memorial_text


class ReportServiceTests(unittest.TestCase):
    def test_memorial_contains_required_sections(self) -> None:
        points = parse_text_coordinates("V-01, 0, 0\nV-02, 30, 0\nV-03, 30, 40")
        closed = ensure_closed(points)
        segments = build_segments(closed)

        memorial = generate_memorial_text(
            property_name="Projeto Teste",
            owner_name="Profissional",
            municipality="Belem",
            state="PA",
            datum="SIRGAS2000",
            coordinate_system="UTM",
            measurement_mode="ponto_a_ponto",
            irradiation_origin_x=None,
            irradiation_origin_y=None,
            irradiation_angle_error_seconds=None,
            area_m2=600.0,
            perimeter_m=120.0,
            segments=segments,
        )

        self.assertIn("MEMORIAL DESCRITIVO", memorial)
        self.assertIn("DESCRICAO DOS LIMITES E CONFRONTACOES", memorial)
        self.assertIn("diretrizes do INCRA", memorial)
        self.assertIn("Provimento CNJ no 65/2017", memorial)

    def test_memorial_rejects_open_polygon_segments(self) -> None:
        points = parse_text_coordinates("V-01, 0, 0\nV-02, 30, 0\nV-03, 30, 40")
        segments = build_segments(points)

        with self.assertRaises(ValueError):
            generate_memorial_text(
                property_name="Projeto Teste",
                owner_name="Profissional",
                municipality="Belem",
                state="PA",
                datum="SIRGAS2000",
                coordinate_system="UTM",
                measurement_mode="ponto_a_ponto",
                irradiation_origin_x=None,
                irradiation_origin_y=None,
                irradiation_angle_error_seconds=None,
                area_m2=600.0,
                perimeter_m=120.0,
                segments=segments,
            )

    def test_exports_generate_non_empty_files(self) -> None:
        points = parse_text_coordinates("V-01, 0, 0\nV-02, 30, 0\nV-03, 30, 40")
        closed = ensure_closed(points)
        segments = build_segments(closed)
        memorial = generate_memorial_text(
            property_name="Projeto Teste",
            owner_name="Profissional",
            municipality="Belem",
            state="PA",
            datum="SIRGAS2000",
            coordinate_system="UTM",
            measurement_mode="ponto_a_ponto",
            irradiation_origin_x=None,
            irradiation_origin_y=None,
            irradiation_angle_error_seconds=None,
            area_m2=600.0,
            perimeter_m=120.0,
            segments=segments,
        )

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            pdf_path = tmp_path / "memorial.pdf"
            docx_path = tmp_path / "memorial.docx"
            dxf_path = tmp_path / "planta.dxf"

            export_pdf(pdf_path, "Memorial", memorial, closed[:-1])
            export_docx(docx_path, "Memorial", memorial, closed[:-1])
            export_dxf(dxf_path, closed[:-1], "Planta")

            self.assertTrue(pdf_path.exists() and pdf_path.stat().st_size > 0)
            self.assertTrue(docx_path.exists() and docx_path.stat().st_size > 0)
            self.assertTrue(dxf_path.exists() and dxf_path.stat().st_size > 0)

    def test_memorial_highlights_irradiation_derived_polygon(self) -> None:
        points = parse_text_coordinates("V-01, 0, 0\nV-02, 30, 0\nV-03, 30, 40")
        closed = ensure_closed(points)
        segments = build_segments(closed)

        memorial = generate_memorial_text(
            property_name="Projeto Teste",
            owner_name="Profissional",
            municipality="Belem",
            state="PA",
            datum="SIRGAS2000",
            coordinate_system="UTM",
            measurement_mode="irradiacao",
            irradiation_origin_x=500000.0,
            irradiation_origin_y=9000000.0,
            irradiation_angle_error_seconds=15.0,
            area_m2=600.0,
            perimeter_m=120.0,
            segments=segments,
        )

        self.assertIn("Poligonal gerada a partir de pontos irradiados.", memorial)
        self.assertIn("Ajuste angular aplicado (segundos): 15.00", memorial)


if __name__ == "__main__":
    unittest.main()
