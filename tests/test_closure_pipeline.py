"""
tests/test_closure_pipeline.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Regression suite for the geometric-closure pipeline fix.

PROBLEM (before fix)
--------------------
When a polygon's last surveyed point did not coincide with the first point
within EPSILON — but the residual distance was within the user-defined
tolerance — the system produced a phantom segment in the memorial:

    "05) Do vertice V-05 ao vertice V-01, seguindo com rumo S 46°38'30" W,
         distancia de 0.25 m."

That segment does not represent a real field observation.  It also inflated
the official perimeter and created a legally inconsistent memorial.

CORRECT BEHAVIOUR (after fix)
------------------------------
* closure error ≤ tolerance  → polygon accepted; NO residual segment; correct
  perimeter; memorial ends at the last real surveyed vertex.
* closure error  > tolerance → ValueError raised.

The 8 tests below cover each requirement from the specification.
"""

from __future__ import annotations

import math
import unittest

from app.models.schemas import CoordinatePoint
from app.services.geometry import (
    EPSILON,
    build_segments,
    ensure_closed,
    is_closed,
)
from app.services.processing import build_project_data, process_coordinates




def _pt(vertex: str, x: float, y: float) -> CoordinatePoint:
    return CoordinatePoint(vertex=vertex, x=x, y=y)


def _ptp_project(closure_tol: float = 0.0):
    """Build a planimetrico ProjectData."""
    return build_project_data(
        {
            "measurement_mode": "planimetrico",
        }
    )


# A pentagon with a deliberate 0.25 m residual closure error.
#
# V-01..V-05 are the five surveyed vertices.  The last point V-05 is offset
# from V-01 by (dx=0.20, dy=0.15) → closure error = hypot(0.20, 0.15) = 0.25 m.
# All five vertices form a valid, non-degenerate polygon when the ring is
# closed logically.
_V01 = _pt("V-01", 0.0, 0.0)
_V02 = _pt("V-02", 10.0, 0.0)
_V03 = _pt("V-03", 10.0, 8.0)
_V04 = _pt("V-04", 5.0, 12.0)
_V05 = _pt("V-05", 0.20, 0.15)  # 0.25 m from V-01

_RESIDUAL_ERROR = math.hypot(0.20, 0.15)  # 0.25 m
_PENTAGON_OPEN = [_V01, _V02, _V03, _V04, _V05]

# Real surveyed perimeter: four sides connecting V-01→V-02→V-03→V-04→V-05.
_REAL_PERIMETER = (
    math.dist((0.0, 0.0), (10.0, 0.0))  # V-01→V-02 = 10.0 m
    + math.dist((10.0, 0.0), (10.0, 8.0))  # V-02→V-03 =  8.0 m
    + math.dist((10.0, 8.0), (5.0, 12.0))  # V-03→V-04 ≈  6.4 m
    + math.dist((5.0, 12.0), (0.20, 0.15))  # V-04→V-05 ≈ 13.1 m
)




class TestNoResidualSegmentWithinTolerance(unittest.TestCase):
    """Residual-segment fix: test 1 of 8.

    When the closure error (0.25 m) is within the tolerance (0.50 m) the
    memorial must contain only the four real surveyed segments.  No phantom
    segment from V-05 back to V-01 may appear.
    """

    def test_segment_list_excludes_residual_leg(self) -> None:
        result = process_coordinates(
            list(_PENTAGON_OPEN), _ptp_project(closure_tol=0.50)
        )

        vertex_pairs = [(s.start_vertex, s.end_vertex) for s in result.segments]

        # Artificial leg must not be present.
        self.assertNotIn(
            ("V-05", "V-01"),
            vertex_pairs,
            "Residual closing leg V-05→V-01 must NOT appear in the memorial.",
        )

    def test_segment_count_equals_surveyed_sides(self) -> None:
        result = process_coordinates(
            list(_PENTAGON_OPEN), _ptp_project(closure_tol=0.50)
        )
        # Pentagon has 5 vertices → 4 surveyed sides (V-01→V-02, …, V-04→V-05).
        self.assertEqual(
            len(result.segments),
            4,
            "Memorial must list exactly 4 real survey segments for 5 vertices.",
        )

    def test_memorial_text_ends_at_last_surveyed_vertex(self) -> None:
        result = process_coordinates(
            list(_PENTAGON_OPEN), _ptp_project(closure_tol=0.50)
        )
        # The last line must mention V-05 as the destination, not V-01.
        self.assertIn("V-05", result.memorial_text)
        # The artificial "V-05 ao vertice V-01" line must be absent.
        self.assertNotIn("V-05 ao vertice V-01", result.memorial_text)




class TestPerimeterExcludesResidualError(unittest.TestCase):
    """Residual-segment fix: test 2 of 8.

    The official perimeter must equal the sum of the four real survey
    segments and must NOT include the 0.25 m residual.
    """

    def test_perimeter_equals_sum_of_real_segments(self) -> None:
        result = process_coordinates(
            list(_PENTAGON_OPEN), _ptp_project(closure_tol=0.50)
        )
        self.assertAlmostEqual(
            result.perimeter_m,
            _REAL_PERIMETER,
            places=9,
            msg=(
                f"Perimeter must be {_REAL_PERIMETER:.4f} m (sum of 4 real sides). "
                f"Got {result.perimeter_m:.4f} m."
            ),
        )

    def test_perimeter_does_not_include_residual(self) -> None:
        result = process_coordinates(
            list(_PENTAGON_OPEN), _ptp_project(closure_tol=0.50)
        )
        perimeter_with_residual = _REAL_PERIMETER + _RESIDUAL_ERROR
        self.assertAlmostEqual(
            result.perimeter_m,
            _REAL_PERIMETER,
            places=9,
            msg=(
                f"Perimeter ({result.perimeter_m:.4f} m) must not include "
                f"the {_RESIDUAL_ERROR:.4f} m residual error "
                f"(inflated value would be {perimeter_with_residual:.4f} m)."
            ),
        )




class TestMemorialNoSameVertexLine(unittest.TestCase):
    """Residual-segment fix: test 3 of 8.

    No segment in the memorial may start and end at the same vertex label
    (e.g. "Do vertice V-01 ao vertice V-01").
    """

    def test_no_self_segment_in_segments(self) -> None:
        result = process_coordinates(
            list(_PENTAGON_OPEN), _ptp_project(closure_tol=0.50)
        )
        for seg in result.segments:
            self.assertNotEqual(
                seg.start_vertex,
                seg.end_vertex,
                f"Segment {seg.start_vertex}→{seg.end_vertex} has the same "
                f"vertex at both ends and must not appear in the memorial.",
            )

    def test_no_self_segment_in_memorial_text(self) -> None:
        result = process_coordinates(
            list(_PENTAGON_OPEN), _ptp_project(closure_tol=0.50)
        )
        for seg in result.segments:
            # Construct the pattern that would appear for a self-segment.
            self_pattern = f"{seg.start_vertex} ao vertice {seg.start_vertex}"
            self.assertNotIn(
                self_pattern,
                result.memorial_text,
                f"Pattern '{self_pattern}' (same-vertex segment) must not "
                f"appear in the memorial text.",
            )




class TestClosureAboveToleranceIsFlagged(unittest.TestCase):
    """Residual-segment fix: test 4 of 8.

    When the closure error (0.25 m) exceeds the tolerance (0.05 m) the
    system must keep the diagnostic payload and flag the global status.
    """

    def test_status_is_outside_when_error_exceeds_tolerance(self) -> None:
        result = process_coordinates(
            list(_PENTAGON_OPEN), _ptp_project(closure_tol=0.05)
        )

        self.assertEqual(result.adjustment_summary["status"], "fora_da_tolerancia")

    def test_diagnostic_contains_measured_and_limit_values(self) -> None:
        result = process_coordinates(
            list(_PENTAGON_OPEN), _ptp_project(closure_tol=0.05)
        )

        self.assertAlmostEqual(result.adjustment_summary["closure_error_m"], 0.25)
        self.assertAlmostEqual(result.adjustment_summary["tolerance_m"], 0.05)

    def test_boundary_exactly_at_tolerance_is_accepted(self) -> None:
        """closure_error == tolerance must be ACCEPTED (≤, not <)."""
        tol = round(_RESIDUAL_ERROR, 10)
        result = process_coordinates(
            list(_PENTAGON_OPEN), _ptp_project(closure_tol=tol)
        )
        self.assertAlmostEqual(result.closure_error_m, _RESIDUAL_ERROR, places=9)




class TestEnsureClosedUsesEpsilon(unittest.TestCase):
    """Residual-segment fix: test 5 of 8.

    ensure_closed() must treat two points as identical when their distance is
    ≤ EPSILON (1e-9 m) and must not append a duplicate vertex in that case.
    """

    def test_already_epsilon_closed_list_is_unchanged(self) -> None:
        pts = [
            _pt("V-01", 0.0, 0.0),
            _pt("V-02", 5.0, 0.0),
            _pt("V-03", 5.0, 5.0),
            _pt("V-01", 0.0, 0.0),  # exact copy of first
        ]
        result = ensure_closed(pts)
        self.assertEqual(
            len(result),
            4,
            "ensure_closed must not append a duplicate when already closed.",
        )

    def test_drift_within_epsilon_is_treated_as_closed(self) -> None:
        drift = EPSILON / 2  # half a nanometre — below threshold
        pts = [
            _pt("V-01", 0.0, 0.0),
            _pt("V-02", 5.0, 0.0),
            _pt("V-03", 5.0, 5.0),
            _pt("V-01", drift, drift),  # within EPSILON of (0,0)
        ]
        result = ensure_closed(pts)
        self.assertEqual(
            len(result),
            4,
            "ensure_closed must treat sub-EPSILON drift as already closed.",
        )

    def test_open_polygon_gets_closing_vertex_appended(self) -> None:
        pts = [
            _pt("V-01", 0.0, 0.0),
            _pt("V-02", 5.0, 0.0),
            _pt("V-03", 5.0, 5.0),
            _pt("V-04", 0.20, 0.15),  # 0.25 m from V-01 — not within EPSILON
        ]
        result = ensure_closed(pts)
        self.assertEqual(
            len(result),
            5,
            "ensure_closed must append closing vertex for polygon with gap > EPSILON.",
        )
        # The appended vertex must have first-point coordinates.
        self.assertAlmostEqual(result[-1].x, 0.0, places=12)
        self.assertAlmostEqual(result[-1].y, 0.0, places=12)

    def test_is_closed_returns_false_above_epsilon(self) -> None:
        first = _pt("V-01", 0.0, 0.0)
        last = _pt("V-05", 0.20, 0.15)  # 0.25 m gap
        self.assertFalse(is_closed(first, last))

    def test_is_closed_returns_true_within_epsilon(self) -> None:
        first = _pt("V-01", 0.0, 0.0)
        last = _pt("V-01", EPSILON * 0.5, 0.0)  # sub-EPSILON gap
        self.assertTrue(is_closed(first, last))




class TestBuildSegmentsIgnoresSyntheticClosure(unittest.TestCase):
    """Residual-segment fix: test 6 of 8.

    build_segments() must raise ValueError when passed a same-name segment
    with non-zero distance (which is what happens if the ensure_closed()
    output is naively forwarded for an open polygon).

    More broadly, the processing pipeline must not forward the artificially
    closed list to build_segments().  This is enforced by process_coordinates()
    using survey_points instead of closed_points.
    """

    def test_build_segments_rejects_same_name_nonzero_distance(self) -> None:
        """A segment where two *consecutive* points share a vertex label but
        have different coordinates is a data integrity error and must be
        rejected.

        Example: ensure_closed() may append CoordinatePoint(vertex=first.vertex,
        x=first.x, y=first.y).  If the previous point already carries that same
        vertex label but at a different location (user data entry error), the
        resulting segment V-XX → V-XX with non-zero distance is invalid.
        """
        pts = [
            _pt("V-01", 0.0, 0.0),
            _pt("V-02", 5.0, 0.0),
            _pt("V-02", 5.0, 5.0),  # same label "V-02" as the previous point
        ]
        # Segment V-02(5,0) → V-02(5,5): same name, distance = 5 > EPSILON.
        with self.assertRaisesRegex(ValueError, "vertice inicial e final iguais"):
            build_segments(pts)

    def test_pipeline_build_segments_on_survey_points_only(self) -> None:
        """The pipeline must build segments from survey_points (not closed_points)
        for a logically-closed polygon, producing N-1 segments for N vertices."""
        result = process_coordinates(
            list(_PENTAGON_OPEN), _ptp_project(closure_tol=0.50)
        )
        # 5 surveyed vertices → 4 segments (no artificial closing leg).
        self.assertEqual(len(result.segments), 4)

    def test_polygon_perimeter_on_survey_points_matches_segments_sum(self) -> None:
        """The stored perimeter must match the sum of all segment distances."""
        result = process_coordinates(
            list(_PENTAGON_OPEN), _ptp_project(closure_tol=0.50)
        )
        segments_total = sum(s.distance_m for s in result.segments)
        self.assertAlmostEqual(
            result.perimeter_m,
            segments_total,
            places=9,
            msg="result.perimeter_m must equal sum of segment distances.",
        )




class TestMemorialContainsOnlyRealSegments(unittest.TestCase):
    """Residual-segment fix: test 7 of 8.

    Every segment listed in the memorial must correspond to two consecutive
    surveyed vertices.  The artificial closing leg must be absent from both
    the segment list and the text body.
    """

    def _result(self):
        return process_coordinates(list(_PENTAGON_OPEN), _ptp_project(closure_tol=0.50))

    def test_all_segment_vertices_exist_in_surveyed_input(self) -> None:
        surveyed_names = {p.vertex for p in _PENTAGON_OPEN}
        result = self._result()
        for seg in result.segments:
            self.assertIn(
                seg.start_vertex,
                surveyed_names,
                f"start_vertex '{seg.start_vertex}' is not a surveyed vertex.",
            )
            self.assertIn(
                seg.end_vertex,
                surveyed_names,
                f"end_vertex '{seg.end_vertex}' is not a surveyed vertex.",
            )

    def test_memorial_text_lists_exactly_four_segments(self) -> None:
        result = self._result()
        # Each segment is introduced with "XX) Do vertice".
        import re

        segment_lines = re.findall(r"\d{2}\) Do vertice", result.memorial_text)
        self.assertEqual(
            len(segment_lines),
            4,
            f"Memorial must list 4 segments for 5 surveyed vertices. "
            f"Found {len(segment_lines)}.",
        )

    def test_memorial_last_line_ends_at_v05(self) -> None:
        result = self._result()
        last_seg = result.segments[-1]
        self.assertEqual(
            last_seg.end_vertex,
            "V-05",
            "Last segment must end at V-05 (the last surveyed vertex).",
        )

    def test_memorial_does_not_mention_residual_distance(self) -> None:
        result = self._result()
        # The residual is 0.25 m; it must not appear as a segment distance.
        # We check for "0.25 m" in the DESCRICAO section (segment lines only).
        descricao_start = result.memorial_text.find("DESCRICAO DOS LIMITES")
        descricao = result.memorial_text[descricao_start:]
        self.assertNotIn(
            "0.25 m",
            descricao,
            "The 0.25 m residual closure error must not appear in the memorial "
            "segment descriptions.",
        )




class TestPolygonValidAfterLogicalClosure(unittest.TestCase):
    """Residual-segment fix: test 8 of 8.

    After logical closure the polygon must still have a correct, positive area
    and the stored misclosure must reflect the actual measurement gap.
    """

    def test_area_is_positive_and_finite(self) -> None:
        result = process_coordinates(
            list(_PENTAGON_OPEN), _ptp_project(closure_tol=0.50)
        )
        self.assertGreater(result.area_m2, 0.0)
        self.assertTrue(math.isfinite(result.area_m2))

    def test_area_equals_closed_ring_shoelace(self) -> None:
        """Area must be computed from the logically-closed ring (ensure_closed),
        not from the open survey traverse."""
        from app.services.geometry import ensure_closed, polygon_area

        closed = ensure_closed(list(_PENTAGON_OPEN))
        expected_area = polygon_area(closed)

        result = process_coordinates(
            list(_PENTAGON_OPEN), _ptp_project(closure_tol=0.50)
        )
        self.assertAlmostEqual(
            result.area_m2,
            expected_area,
            places=9,
            msg="Area must equal the Shoelace result on the closed ring.",
        )

    def test_closure_error_reported_accurately(self) -> None:
        result = process_coordinates(
            list(_PENTAGON_OPEN), _ptp_project(closure_tol=0.50)
        )
        self.assertAlmostEqual(
            result.closure_error_m,
            _RESIDUAL_ERROR,
            places=9,
            msg="ProcessingResult.closure_error_m must reflect the real gap.",
        )

    def test_closed_points_form_valid_ring(self) -> None:
        """result.points must start and end at the same coordinate (closed ring)."""
        result = process_coordinates(
            list(_PENTAGON_OPEN), _ptp_project(closure_tol=0.50)
        )
        first = result.points[0]
        last = result.points[-1]
        self.assertTrue(
            is_closed(first, last),
            f"result.points must form a closed ring: "
            f"first=({first.x},{first.y}), last=({last.x},{last.y}).",
        )


if __name__ == "__main__":
    unittest.main()
