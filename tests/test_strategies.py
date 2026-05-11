from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.models.schemas import CoordinatePoint
from app.services.irradiation import irradiation_to_points
from app.services.strategies.export import ExportPayload, ExportStrategyFactory
from app.services.strategies.parsing import ParsingStrategyFactory


class ParsingStrategyFactoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.factory = ParsingStrategyFactory()

    def test_selects_csv_strategy_for_csv_extension(self) -> None:
        strategy = self.factory.for_upload_name("dados.csv")
        points = strategy.parse(b"vertex,x,y\nV-01,0,0\nV-02,1,0\nV-03,1,1\n")
        self.assertEqual(len(points), 3)

    def test_selects_shapefile_strategy_for_zip_extension(self) -> None:
        strategy = self.factory.for_upload_name("dados.zip")
        self.assertEqual(strategy.__class__.__name__, "ShapefileZipParsingStrategy")

    def test_selects_irradiation_strategy_for_csv_extension(self) -> None:
        strategy = self.factory.for_irradiation_upload_name("observacoes.csv")
        observations = strategy.parse(
            b"vertex,estacao_x,estacao_y,azimute,distancia\nV-01,100,200,0,10\nV-02,100,200,90,10\nV-03,100,200,180,10\n"
        )
        self.assertEqual(len(observations), 3)
        self.assertAlmostEqual(observations[0].station_x or 0.0, 100.0, places=6)

    def test_parses_irradiation_azimuth_in_dms(self) -> None:
        strategy = self.factory.for_irradiation_text()
        observations = strategy.parse("V-01, 15°30'00\", 10\nV-02, 90°00'00\", 10\nV-03, 180°00'00\", 10")
        self.assertAlmostEqual(observations[0].azimuth_deg, 15.5, places=6)

    def test_parses_irradiation_with_station_per_observation(self) -> None:
        strategy = self.factory.for_irradiation_text()
        observations = strategy.parse(
            "V-01, 500000, 9000000, 15, 10\nV-02, 500002, 9000001, 90, 10\nV-03, 500003, 9000002, 180, 10"
        )
        self.assertAlmostEqual(observations[1].station_x or 0.0, 500002.0, places=6)
        self.assertAlmostEqual(observations[1].station_y or 0.0, 9000001.0, places=6)

    def test_irradiation_conversion_builds_cartesian_points(self) -> None:
        strategy = self.factory.for_irradiation_text()
        observations = strategy.parse("V-01, 0, 10\nV-02, 90, 10\nV-03, 180, 10")
        points = irradiation_to_points(observations, origin_x=100.0, origin_y=200.0)

        self.assertAlmostEqual(points[0].x, 100.0, places=6)
        self.assertAlmostEqual(points[0].y, 210.0, places=6)
        self.assertAlmostEqual(points[1].x, 110.0, places=6)
        self.assertAlmostEqual(points[1].y, 200.0, places=6)

    def test_irradiation_conversion_orders_points_by_azimuth(self) -> None:
        strategy = self.factory.for_irradiation_text()
        observations = strategy.parse("V-01, 300, 10\nV-02, 20, 10\nV-03, 150, 10")
        points = irradiation_to_points(observations, origin_x=0.0, origin_y=0.0)

        self.assertEqual([point.vertex for point in points], ["V-02", "V-03", "V-01"])

    def test_irradiation_conversion_uses_station_in_each_observation(self) -> None:
        strategy = self.factory.for_irradiation_text()
        observations = strategy.parse(
            "V-01, 100, 200, 0, 10\nV-02, 110, 200, 90, 10\nV-03, 110, 210, 180, 10"
        )
        points = irradiation_to_points(observations)

        self.assertAlmostEqual(points[0].x, 100.0, places=6)
        self.assertAlmostEqual(points[0].y, 210.0, places=6)
        self.assertAlmostEqual(points[1].x, 120.0, places=6)
        self.assertAlmostEqual(points[1].y, 200.0, places=6)

    def test_irradiation_conversion_applies_angular_error_seconds(self) -> None:
        strategy = self.factory.for_irradiation_text()
        observations = strategy.parse("V-01, 0, 10\nV-02, 90, 10\nV-03, 180, 10")
        points = irradiation_to_points(observations, origin_x=100.0, origin_y=200.0, angle_error_seconds=3600.0)

        self.assertAlmostEqual(points[0].x, 100.174524, places=6)
        self.assertAlmostEqual(points[0].y, 209.998477, places=6)

    def test_rejects_irradiation_with_invalid_azimuth_prefix(self) -> None:
        strategy = self.factory.for_irradiation_text()
        with self.assertRaises(ValueError):
            strategy.parse('V-01, Az 90°00\'00", 100\nV-02, 180, 100\nV-03, 270, 100')

    def test_rejects_irradiation_with_non_positive_distance(self) -> None:
        strategy = self.factory.for_irradiation_text()
        observations = strategy.parse("V-01, 0, 120\nV-02, 90, 0\nV-03, 180, 85")
        with self.assertRaisesRegex(ValueError, "A distancia da irradiacao deve ser maior que zero."):
            irradiation_to_points(observations, origin_x=500000.0, origin_y=9000000.0)

    def test_rejects_irradiation_with_less_than_three_observations(self) -> None:
        strategy = self.factory.for_irradiation_text()
        observations = strategy.parse("V-01, 0, 120\nV-02, 90, 100")
        with self.assertRaisesRegex(ValueError, "Informe ao menos 3 observacoes de irradiacao"):
            irradiation_to_points(observations, origin_x=500000.0, origin_y=9000000.0)

    def test_rejects_irradiation_without_station_reference(self) -> None:
        strategy = self.factory.for_irradiation_text()
        observations = strategy.parse("V-01, 0, 120\nV-02, 90, 100\nV-03, 180, 80")
        with self.assertRaisesRegex(ValueError, "informe X e Y da estacao"):
            irradiation_to_points(observations)


class ExportStrategyFactoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.factory = ExportStrategyFactory()
        self.points = [
            CoordinatePoint(vertex="V-01", x=0.0, y=0.0),
            CoordinatePoint(vertex="V-02", x=10.0, y=0.0),
            CoordinatePoint(vertex="V-03", x=10.0, y=10.0),
        ]

    def test_exports_pdf_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = ExportPayload(
                property_name="Projeto Teste",
                points=self.points,
                memorial_text="Memorial de teste",
                output_dir=Path(tmp),
                slug="projeto_teste",
                token="abcd1234",
            )
            strategy = self.factory.for_output_format("pdf")
            result = strategy.export(payload)

            self.assertTrue(result.path.exists())
            self.assertTrue(result.path.name.endswith(".pdf"))

    def test_rejects_invalid_export_format(self) -> None:
        with self.assertRaises(ValueError):
            self.factory.for_output_format("xlsx")


if __name__ == "__main__":
    unittest.main()
