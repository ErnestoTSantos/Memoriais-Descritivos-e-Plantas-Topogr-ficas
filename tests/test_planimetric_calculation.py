from __future__ import annotations

import math
import unittest

from app.models.schemas import CoordinatePoint
from app.services.processing import build_project_data, process_coordinates


def _pt(vertex: str, x: float, y: float) -> CoordinatePoint:
    return CoordinatePoint(vertex=vertex, x=x, y=y)


def _project(**extra):
    raw = {
        "measurement_mode": "planimetrico",
    }
    raw.update(extra)
    return build_project_data(raw)


class PlanimetricCalculationTableTests(unittest.TestCase):
    def test_each_table_row_contains_all_required_manual_columns(self) -> None:
        result = process_coordinates(
            [_pt("A", 0, 0), _pt("B", 10, 0), _pt("C", 10, 10), _pt("D", 0, 10)],
            _project(),
        )

        row = result.planimetric_table.segments[0].model_dump()
        required = {
            "segment",
            "station",
            "point_initial",
            "point_final",
            "distance",
            "observed_angle",
            "angular_adjustment",
            "corrected_angle",
            "azimuth",
            "bearing",
            "east_positive",
            "west_negative",
            "north_positive",
            "south_negative",
            "delta_x",
            "delta_y",
            "closure_error_x",
            "closure_error_y",
            "correction_x",
            "correction_y",
            "adjusted_x",
            "adjusted_y",
            "accumulated_x",
            "accumulated_y",
            "error_contribution_percent",
            "correction_applied",
            "status",
            "messages",
        }

        self.assertTrue(required.issubset(row.keys()))
        self.assertEqual(row["segment"], "A-B")
        self.assertEqual(row["station"], "A")

    def test_projections_azimuths_bearings_and_accumulated_coordinates(self) -> None:
        result = process_coordinates(
            [_pt("A", 0, 0), _pt("B", 10, 0), _pt("C", 10, 10), _pt("D", 0, 10)],
            _project(),
        )
        rows = result.planimetric_table.segments

        self.assertAlmostEqual(rows[0].east_positive, 10.0, places=9)
        self.assertAlmostEqual(rows[0].west_negative, 0.0, places=9)
        self.assertAlmostEqual(rows[0].north_positive, 0.0, places=9)
        self.assertAlmostEqual(rows[0].south_negative, 0.0, places=9)
        self.assertEqual(rows[0].azimuth, "090°00'00\"")
        self.assertIn("E", rows[0].bearing)
        self.assertAlmostEqual(rows[0].accumulated_x, 10.0, places=9)
        self.assertAlmostEqual(rows[0].accumulated_y, 0.0, places=9)

        self.assertAlmostEqual(rows[1].north_positive, 10.0, places=9)
        self.assertAlmostEqual(rows[2].west_negative, -10.0, places=9)
        self.assertAlmostEqual(rows[3].south_negative, -10.0, places=9)
        self.assertAlmostEqual(rows[-1].accumulated_x, 0.0, places=9)
        self.assertAlmostEqual(rows[-1].accumulated_y, 0.0, places=9)

    def test_angular_adjustment_and_corrected_angle_are_serialized(self) -> None:
        result = process_coordinates(
            [_pt("A", 0, 0), _pt("B", 10, 0), _pt("C", 10, 10)],
            _project(
                equipment_angular_error_seconds="30",
            ),
        )

        row = result.planimetric_table.segments[0]
        self.assertEqual(row.angular_adjustment, '+30.00"')
        self.assertAlmostEqual(row.angular_adjustment_seconds, 30.0, places=9)
        self.assertAlmostEqual(
            row.corrected_angle_deg,
            (row.observed_angle_deg or 0.0) + 30.0 / 3600.0,
            places=9,
        )

    def test_bowditch_corrections_closure_and_contribution_are_auditable(self) -> None:
        points = [
            _pt("A", 0.0, 0.0),
            _pt("B", 10.0, 0.0),
            _pt("C", 5.0, 10.0),
            _pt("A", 0.20, 0.15),
        ]
        result = process_coordinates(points, _project())
        table = result.planimetric_table
        summary = table.summary

        self.assertAlmostEqual(summary.closure_error_x, 0.20, places=9)
        self.assertAlmostEqual(summary.closure_error_y, 0.15, places=9)
        self.assertAlmostEqual(summary.linear_error, math.hypot(0.20, 0.15), places=9)
        self.assertAlmostEqual(summary.correction_sum_x, -0.20, places=9)
        self.assertAlmostEqual(summary.correction_sum_y, -0.15, places=9)
        self.assertAlmostEqual(
            summary.final_adjusted_coordinate_x or 0.0, 0.0, places=9
        )
        self.assertAlmostEqual(
            summary.final_adjusted_coordinate_y or 0.0, 0.0, places=9
        )
        self.assertAlmostEqual(
            sum(row.error_contribution_percent for row in table.segments),
            100.0,
            places=9,
        )
        self.assertTrue(any(row.correction_applied > 0 for row in table.segments))

    def test_summary_exposes_area_perimeter_tolerance_status_and_formulas(self) -> None:
        result = process_coordinates(
            [_pt("A", 0, 0), _pt("B", 10, 0), _pt("C", 10, 10), _pt("D", 0, 10)],
            _project(),
        )
        table = result.planimetric_table

        self.assertAlmostEqual(table.summary.area, 100.0, places=9)
        self.assertAlmostEqual(table.summary.perimeter, 40.0, places=9)
        self.assertAlmostEqual(table.summary.tolerance or 0.0, 0.05, places=9)
        self.assertEqual(table.summary.status, "dentro_da_tolerancia")
        self.assertIn("bowditch_x", table.formulas)
        self.assertIn("coordenada_acumulada_x", table.formulas)


if __name__ == "__main__":
    unittest.main()
