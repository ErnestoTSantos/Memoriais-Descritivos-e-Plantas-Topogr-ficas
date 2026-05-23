from __future__ import annotations

import json
import math
import os
import unittest

from app.models.schemas import IrradiationObservation, TraverseObservation
from app.services.angles import parse_azimuth
from app.services.processing import ProjectData, Station, process_coordinates, process_traverse


ANGULAR_ALERT = (
    "Erro angular acima da precisão informada do equipamento. Revise as observações."
)


def _project(
    *,
    mode: str = "planimetrico",
    angular_error_seconds: float | None = 30.0,
    stations: list[Station] | None = None,
) -> ProjectData:
    return ProjectData(
        property_name="Casos beta",
        owner_name="Equipe QA",
        municipality="Campinas",
        state="SP",
        datum="SIRGAS2000",
        coordinate_system="UTM",
        measurement_mode=mode,
        stations=stations or [],
        equipment_angular_error_seconds=angular_error_seconds,
    )


def _trav(
    station: str,
    sighted_point: str,
    distance_m: float,
    observed_angle_dms: str,
) -> TraverseObservation:
    return TraverseObservation(
        station=station,
        sighted_point=sighted_point,
        distance_m=distance_m,
        observed_angle_deg=parse_azimuth(observed_angle_dms),
        observed_angle_dms=observed_angle_dms,
    )


def _irr(
    vertex: str,
    distance_m: float,
    azimuth_dms: str,
    station_name: str | None = None,
) -> IrradiationObservation:
    return IrradiationObservation(
        vertex=vertex,
        distance_m=distance_m,
        azimuth_deg=parse_azimuth(azimuth_dms),
        station_name=station_name,
    )


def _assert_projection_identity(testcase: unittest.TestCase, segment) -> None:
    azimuth_rad = math.radians(segment.azimuth_deg)
    testcase.assertAlmostEqual(
        segment.delta_e_m,
        segment.distance_m * math.sin(azimuth_rad),
        places=9,
    )
    testcase.assertAlmostEqual(
        segment.delta_n_m,
        segment.distance_m * math.cos(azimuth_rad),
        places=9,
    )
    testcase.assertAlmostEqual(
        segment.adjusted_delta_e_m,
        segment.delta_e_m + segment.correction_e_m,
        places=9,
    )
    testcase.assertAlmostEqual(
        segment.adjusted_delta_n_m,
        segment.delta_n_m + segment.correction_n_m,
        places=9,
    )


class BetaTraverseComplexCasesTests(unittest.TestCase):
    """Regression fixtures requested for beta validation.

    Documented expected values:
    - Caso 1: angular sum 360°01'18", misclosure +78", correction -19.5"/angle.
    - Caso 2: angular sum 360°03'50", misclosure +230", tolerance 10"*4 = 40".
    - Caso 3: perimeter 60.027 m, adjusted area close to 200 m2.
    """

    def test_case_1_small_angular_error_is_distributed_and_bowditch_closes(self) -> None:
        result = process_traverse(
            [
                _trav("A", "B", 12.391, "102°16'58\""),
                _trav("B", "C", 25.023, "89°36'33\""),
                _trav("C", "D", 17.659, "65°41'15\""),
                _trav("D", "A", 18.962, "102°26'32\""),
            ],
            _project(angular_error_seconds=30.0),
            initial_azimuth_deg=292.515,
        )

        angular = result.traverse_angular_summary
        self.assertIsNotNone(angular)
        self.assertAlmostEqual(angular.angular_misclosure_seconds, 78.0, places=6)
        self.assertAlmostEqual(angular.correction_per_side_seconds, -19.5, places=6)
        self.assertEqual(angular.status, "ok")
        self.assertAlmostEqual(angular.allowed_error_seconds or 0.0, 120.0, places=6)

        expected_corrected_angles = [
            parse_azimuth("102°16'38.5\""),
            parse_azimuth("89°36'13.5\""),
            parse_azimuth("65°40'55.5\""),
            parse_azimuth("102°26'12.5\""),
        ]
        for row, expected in zip(
            result.planimetric_table.segments,
            expected_corrected_angles,
            strict=True,
        ):
            self.assertAlmostEqual(row.corrected_angle_deg or 0.0, expected, places=9)

        expected_azimuths = [
            292.515,
            22.11875,
            87.800833333333,
            190.237638888889,
        ]
        for segment, expected_azimuth in zip(
            result.segments,
            expected_azimuths,
            strict=True,
        ):
            self.assertAlmostEqual(segment.azimuth_deg, expected_azimuth, places=9)
            _assert_projection_identity(self, segment)

        self.assertGreater(result.closure_error_m, 0.0)
        self.assertAlmostEqual(
            sum(segment.adjusted_delta_e_m for segment in result.segments),
            0.0,
            places=9,
        )
        self.assertAlmostEqual(
            sum(segment.adjusted_delta_n_m for segment in result.segments),
            0.0,
            places=9,
        )
        self.assertAlmostEqual(result.adjusted_points[-1].x, 0.0, places=9)
        self.assertAlmostEqual(result.adjusted_points[-1].y, 0.0, places=9)
        self.assertIn("memorial", result.memorial_text.lower())
        self.assertEqual(len(result.planimetric_table.segments), 4)

    def test_case_2_large_angular_error_returns_audit_table_with_alert(self) -> None:
        result = process_traverse(
            [
                _trav("A", "B", 12.391, "102°17'30\""),
                _trav("B", "C", 25.023, "89°37'10\""),
                _trav("C", "D", 17.659, "65°41'50\""),
                _trav("D", "A", 18.962, "102°27'20\""),
            ],
            _project(angular_error_seconds=10.0),
            initial_azimuth_deg=292.515,
        )

        angular = result.traverse_angular_summary
        self.assertIsNotNone(angular)
        self.assertAlmostEqual(angular.angular_misclosure_seconds, 230.0, places=6)
        self.assertAlmostEqual(angular.allowed_error_seconds or 0.0, 40.0, places=6)
        self.assertEqual(angular.status, "warning")
        self.assertEqual(angular.status_label, ANGULAR_ALERT)
        self.assertIn(ANGULAR_ALERT, result.adjustment_summary["messages"])
        self.assertEqual(len(result.planimetric_table.segments), 4)

    def test_case_3_linear_misclosure_uses_bowditch_without_recomputing_from_quadrants(self) -> None:
        result = process_traverse(
            [
                _trav("A", "B", 20.012, "90°00'08\""),
                _trav("B", "C", 10.006, "89°59'54\""),
                _trav("C", "D", 20.018, "90°00'11\""),
                _trav("D", "A", 9.991, "89°59'47\""),
            ],
            _project(angular_error_seconds=20.0),
            initial_azimuth_deg=90.0,
        )

        angular = result.traverse_angular_summary
        self.assertIsNotNone(angular)
        self.assertAlmostEqual(angular.angular_misclosure_seconds, 0.0, places=9)
        self.assertLess(result.closure_error_m, 0.02)
        self.assertAlmostEqual(result.perimeter_m, 60.027, places=6)
        self.assertAlmostEqual(result.area_m2, 200.12, delta=0.25)

        for segment, row in zip(
            result.segments,
            result.planimetric_table.segments,
            strict=True,
        ):
            _assert_projection_identity(self, segment)
            self.assertAlmostEqual(
                row.adjusted_delta_x,
                row.delta_x + row.correction_x,
                places=9,
            )
            self.assertAlmostEqual(
                row.adjusted_delta_y,
                row.delta_y + row.correction_y,
                places=9,
            )

        self.assertAlmostEqual(result.adjusted_points[-1].x, 0.0, places=9)
        self.assertAlmostEqual(result.adjusted_points[-1].y, 0.0, places=9)


class BetaIrradiationComplexCasesTests(unittest.TestCase):
    """Regression fixtures for irradiation quadrants, near-axis azimuths and alerts."""

    def test_case_4_single_station_quadrants_and_table_rows(self) -> None:
        result = process_coordinates(
            [
                _irr("P1", 50.0, "44°59'50\""),
                _irr("P2", 50.0, "135°00'12\""),
                _irr("P3", 50.0, "225°00'18\""),
                _irr("P4", 50.0, "314°59'45\""),
            ],
            _project(
                mode="irradiacao",
                angular_error_seconds=20.0,
                stations=[Station("E1", 1000.0, 1000.0)],
            ),
        )

        self.assertIsNotNone(result.irradiation_table)
        rows = {row.vertex: row for row in result.irradiation_table.rows}
        self.assertGreater(rows["P1"].delta_x, 0.0)
        self.assertGreater(rows["P1"].delta_y, 0.0)
        self.assertGreater(rows["P2"].delta_x, 0.0)
        self.assertLess(rows["P2"].delta_y, 0.0)
        self.assertLess(rows["P3"].delta_x, 0.0)
        self.assertLess(rows["P3"].delta_y, 0.0)
        self.assertLess(rows["P4"].delta_x, 0.0)
        self.assertGreater(rows["P4"].delta_y, 0.0)

        self.assertAlmostEqual(result.area_m2, 5000.0, delta=1.0)
        self.assertAlmostEqual(result.perimeter_m, 282.84, delta=0.1)
        self.assertLessEqual(
            result.adjustment_summary["observed_angular_deviation_seconds"],
            20.0,
        )
        self.assertEqual(len(result.planimetric_table.segments), 4)

    def test_case_5_multiple_stations_near_axes_keep_correct_signs_and_grouping(self) -> None:
        result = process_coordinates(
            [
                _irr("A", 40.0, "0°00'12\"", "E1"),
                _irr("B", 60.0, "89°59'48\"", "E1"),
                _irr("C", 45.0, "180°00'10\"", "E2"),
                _irr("D", 55.0, "270°00'15\"", "E2"),
            ],
            _project(
                mode="irradiacao",
                angular_error_seconds=15.0,
                stations=[Station("E1", 500.0, 500.0), Station("E2", 600.0, 500.0)],
            ),
        )

        self.assertIsNotNone(result.irradiation_table)
        rows = {row.vertex: row for row in result.irradiation_table.rows}
        self.assertEqual(
            [row.station_name for row in result.irradiation_table.rows],
            ["E1", "E1", "E2", "E2"],
        )
        self.assertGreater(rows["A"].delta_y, 0.0)
        self.assertAlmostEqual(rows["A"].delta_x, 0.0, delta=0.01)
        self.assertGreater(rows["B"].delta_x, 0.0)
        self.assertAlmostEqual(rows["B"].delta_y, 0.0, delta=0.01)
        self.assertLess(rows["C"].delta_y, 0.0)
        self.assertAlmostEqual(rows["C"].delta_x, 0.0, delta=0.01)
        self.assertLess(rows["D"].delta_x, 0.0)
        self.assertAlmostEqual(rows["D"].delta_y, 0.0, delta=0.01)
        self.assertEqual(len(result.segments), 4)

    def test_case_6_irradiation_above_equipment_precision_keeps_results_and_alerts(self) -> None:
        result = process_coordinates(
            [
                _irr("P1", 100.0, "45°00'30\""),
                _irr("P2", 100.0, "135°00'40\""),
                _irr("P3", 100.0, "225°00'35\""),
                _irr("P4", 100.0, "315°00'45\""),
            ],
            _project(
                mode="irradiacao",
                angular_error_seconds=5.0,
                stations=[Station("E1", 100.0, 100.0)],
            ),
        )

        self.assertIsNotNone(result.irradiation_table)
        self.assertEqual(result.adjustment_summary["angular_status"], "fora_da_tolerancia")
        self.assertGreater(
            result.adjustment_summary["observed_angular_deviation_seconds"],
            5.0,
        )
        self.assertIn(ANGULAR_ALERT, result.adjustment_summary["messages"])
        self.assertAlmostEqual(result.area_m2, 20000.0, delta=2.0)
        self.assertAlmostEqual(result.perimeter_m, 565.69, delta=0.2)


@unittest.skipUnless(
    os.getenv("DJANGO_SETTINGS_MODULE"),
    "Django integration tests require manage.py test.",
)
class BetaApiResponseTests(unittest.TestCase):
    def test_case_1_api_response_exposes_tables_and_memorial(self) -> None:
        from django.test import Client

        payload = {
            "property_name": "Casos beta",
            "owner_name": "Equipe QA",
            "municipality": "Campinas",
            "state": "SP",
            "datum": "SIRGAS2000",
            "coordinate_system": "UTM",
            "measurement_mode": "planimetrico",
            "equipment_angular_error_seconds": "30",
            "initial_azimuth_deg": 292.515,
            "traverse_observations": json.dumps(
                [
                    {
                        "station": "A",
                        "sighted_point": "B",
                        "distance_m": 12.391,
                        "observed_angle_deg": parse_azimuth("102°16'58\""),
                    },
                    {
                        "station": "B",
                        "sighted_point": "C",
                        "distance_m": 25.023,
                        "observed_angle_deg": parse_azimuth("89°36'33\""),
                    },
                    {
                        "station": "C",
                        "sighted_point": "D",
                        "distance_m": 17.659,
                        "observed_angle_deg": parse_azimuth("65°41'15\""),
                    },
                    {
                        "station": "D",
                        "sighted_point": "A",
                        "distance_m": 18.962,
                        "observed_angle_deg": parse_azimuth("102°26'32\""),
                    },
                ]
            ),
        }

        response = Client().post("/api/process", data=payload)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["measurement_mode"], "planimetrico")
        self.assertEqual(len(data["segments"]), 4)
        self.assertEqual(len(data["planimetric_table"]["segments"]), 4)
        self.assertIn("formulas", data["planimetric_table"])
        self.assertAlmostEqual(
            data["traverse_angular_summary"]["angular_misclosure_seconds"],
            78.0,
            places=6,
        )
        self.assertIn("memorial_text", data)
