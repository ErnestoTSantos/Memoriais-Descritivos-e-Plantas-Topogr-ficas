from __future__ import annotations

import math

from app.models.schemas import CoordinatePoint, SegmentInfo
from app.services.angles import decimal_to_dms

# EPSILON is used for comparisons in Cartesian space (UTM coordinates in metres
# or small local coordinate systems).  1e-9 m ≈ 1 nanometre, well below any
# survey instrument precision.
EPSILON: float = 1e-9

# Maximum supported vertex count.  The O(n²) self-intersection check is the
# bottleneck: 5 000 vertices → ~12.5M segment pairs, which is already slow.
# This guard prevents DoS via pathological large payloads.
MAX_VERTICES: int = 5_000


def adaptive_epsilon(points: list[CoordinatePoint]) -> float:
    """Return a tolerance scaled to the bounding box of *points*.

    For UTM coordinates (magnitudes ~1e5–1e7) a fixed EPSILON=1e-9 is fine.
    For geographic coordinates (magnitudes ~1e-1–1e2) the same EPSILON is also
    fine.  However the function is kept for callers that need an explicit
    relative tolerance proportional to coordinate magnitude, e.g. when mixing
    geographic and projected systems dynamically.

    Returns EPSILON when the bounding box diagonal is zero or not finite.
    """
    if not points:
        return EPSILON
    xs = [p.x for p in points if math.isfinite(p.x)]
    ys = [p.y for p in points if math.isfinite(p.y)]
    if not xs or not ys:
        return EPSILON
    diagonal = math.hypot(max(xs) - min(xs), max(ys) - min(ys))
    if not math.isfinite(diagonal) or diagonal == 0.0:
        return EPSILON
    # Use a relative tolerance of 1e-9 times the bounding-box diagonal,
    # but never smaller than EPSILON (1 nm) nor larger than 1e-3 (1 mm).
    return max(EPSILON, min(1e-3, diagonal * 1e-9))


def _format_dms(angle_deg: float) -> str:
    dms = decimal_to_dms(angle_deg)
    deg, rest = dms.split("°", maxsplit=1)
    return f"{int(deg):02d}°{rest}"


def azimuth_to_bearing(azimuth_deg: float) -> str:
    az = azimuth_deg % 360
    if 0 <= az < 90:
        return f"N {_format_dms(az)} E"
    if 90 <= az < 180:
        return f"S {_format_dms(180 - az)} E"
    if 180 <= az < 270:
        return f"S {_format_dms(az - 180)} W"
    return f"N {_format_dms(360 - az)} W"


def is_closed(first: CoordinatePoint, last: CoordinatePoint, eps: float = EPSILON) -> bool:
    """Return True if *first* and *last* represent the same vertex position.

    Uses EPSILON-based comparison instead of exact float equality to handle
    round-trip floating-point drift in coordinates.

    This is the **single authoritative closure check** — both geometry.py and
    reports.py must call this function so the criterion is always consistent.
    """
    return abs(first.x - last.x) <= eps and abs(first.y - last.y) <= eps


def ensure_closed(points: list[CoordinatePoint]) -> list[CoordinatePoint]:
    """Append a copy of the first point if the polygon is not already closed.

    Uses EPSILON comparison (not exact equality) so floating-point drift from
    CSV parsing / shapefile loading does not cause spurious duplication.
    """
    if not points:
        return points
    first = points[0]
    last = points[-1]
    if is_closed(first, last):
        return points
    closed = points.copy()
    closed.append(CoordinatePoint(vertex=first.vertex, x=first.x, y=first.y))
    return closed


def signed_polygon_area(points: list[CoordinatePoint]) -> float:
    """Return the signed area using the shoelace formula.

    Positive → counter-clockwise (CCW) orientation.
    Negative → clockwise (CW) orientation.

    Raises ValueError for fewer than 3 points, which cannot form a polygon.
    Uses a translated origin (first vertex) to improve numerical stability for
    large UTM coordinates.
    """
    if len(points) < 3:
        raise ValueError(
            "Sao necessarios ao menos 3 pontos para calcular a area do poligono."
        )

    origin_x = points[0].x
    origin_y = points[0].y
    acc = 0.0
    for i in range(len(points) - 1):
        x1 = points[i].x - origin_x
        y1 = points[i].y - origin_y
        x2 = points[i + 1].x - origin_x
        y2 = points[i + 1].y - origin_y
        acc += x1 * y2 - x2 * y1
    return acc / 2.0


def polygon_area(points: list[CoordinatePoint]) -> float:
    """Return the unsigned (absolute) polygon area in coordinate-system units².

    Raises ValueError for fewer than 3 points.
    """
    return abs(signed_polygon_area(points))


def polygon_perimeter(points: list[CoordinatePoint]) -> float:
    total = 0.0
    for i in range(len(points) - 1):
        dx = points[i + 1].x - points[i].x
        dy = points[i + 1].y - points[i].y
        total += math.hypot(dx, dy)
    return total


def closure_error(points: list[CoordinatePoint]) -> float:
    if len(points) < 2:
        return 0.0
    first = points[0]
    last = points[-1]
    return math.hypot(last.x - first.x, last.y - first.y)


def build_segments(
    points: list[CoordinatePoint], angle_error_seconds: float = 0.0
) -> list[SegmentInfo]:
    """Build SegmentInfo list from a sequence of CoordinatePoints.

    [F-10] Segments with distance ≤ EPSILON (zero-distance) are rejected with a
    clear ValueError.  Previously atan2(0, 0) returned 0 silently, producing a
    phantom azimuth of 0° with no distance.
    """
    segments: list[SegmentInfo] = []
    for i in range(len(points) - 1):
        start = points[i]
        end = points[i + 1]
        dx = end.x - start.x
        dy = end.y - start.y
        distance = math.hypot(dx, dy)

        if distance <= EPSILON:
            raise ValueError(
                f"Segmento {start.vertex}→{end.vertex} tem distância zero ou nula "
                f"({distance:.2e} m). Pontos consecutivos identicos nao sao permitidos."
            )

        if start.vertex == end.vertex and distance > EPSILON:
            raise ValueError(
                f"Segmento invalido: vertice inicial e final iguais ('{start.vertex}') "
                f"com distancia nao nula ({distance:.2f} m)."
            )

        azimuth = (math.degrees(math.atan2(dx, dy)) + 360) % 360
        adjusted_azimuth = (azimuth + (angle_error_seconds / 3600.0)) % 360.0
        segments.append(
            SegmentInfo(
                start_vertex=start.vertex,
                end_vertex=end.vertex,
                distance_m=distance,
                azimuth_deg=azimuth,
                azimuth_dms=decimal_to_dms(azimuth),
                azimuth_adjusted_deg=adjusted_azimuth,
                azimuth_adjusted_dms=decimal_to_dms(adjusted_azimuth),
                applied_angle_error_seconds=angle_error_seconds,
                bearing=azimuth_to_bearing(adjusted_azimuth),
            )
        )
    return segments


def validate_points(points: list[CoordinatePoint]) -> None:
    """Validate that *points* can form a legal polygon.

    Order of checks (critical):
    1. Minimum count.
    2. **NaN/Inf check first** — before any set() or arithmetic operations.
       float('nan') != float('nan'), so a NaN coordinate in a set() will never
       match another NaN, masking duplicates and producing wrong counts.
    3. Strip optional closing duplicate.
    4. Unique-coordinate deduplication.

    [F-04] NaN/Inf validation was previously the *last* check, allowing NaN to
    corrupt the set() deduplication logic.
    [F-22] Vertex count is capped at MAX_VERTICES to prevent DoS via the O(n²)
    self-intersection check.
    """
    if len(points) < 3:
        raise ValueError("Sao necessarios ao menos 3 pontos para formar um poligono.")

    if len(points) > MAX_VERTICES:
        raise ValueError(
            f"Numero de vertices ({len(points)}) excede o limite maximo ({MAX_VERTICES}). "
            "Simplifique a geometria antes de processar."
        )

    for point in points:
        if not math.isfinite(point.x) or not math.isfinite(point.y):
            raise ValueError(
                f"Coordenada invalida no vertice '{point.vertex}': "
                f"X={point.x}, Y={point.y}. Valores devem ser numericos e finitos."
            )

    canonical_points = points
    if len(points) > 1 and is_closed(points[0], points[-1]):
        canonical_points = points[:-1]

    if len(canonical_points) < 3:
        raise ValueError("Sao necessarios ao menos 3 pontos distintos para formar um poligono.")

    unique_pairs = {(p.x, p.y) for p in canonical_points}
    if len(unique_pairs) < 3:
        raise ValueError(
            "Coordenadas insuficientes ou repetidas para formar um poligono valido."
        )

    if len(unique_pairs) != len(canonical_points):
        raise ValueError("Coordenadas duplicadas nao sao permitidas no poligono.")


def _orientation(a: CoordinatePoint, b: CoordinatePoint, c: CoordinatePoint) -> int:
    value = (b.y - a.y) * (c.x - b.x) - (b.x - a.x) * (c.y - b.y)
    if abs(value) <= EPSILON:
        return 0
    return 1 if value > 0 else 2


def _on_segment(a: CoordinatePoint, b: CoordinatePoint, c: CoordinatePoint) -> bool:
    return (
        min(a.x, c.x) - EPSILON <= b.x <= max(a.x, c.x) + EPSILON
        and min(a.y, c.y) - EPSILON <= b.y <= max(a.y, c.y) + EPSILON
    )


def _segments_intersect(
    p1: CoordinatePoint,
    q1: CoordinatePoint,
    p2: CoordinatePoint,
    q2: CoordinatePoint,
) -> bool:
    o1 = _orientation(p1, q1, p2)
    o2 = _orientation(p1, q1, q2)
    o3 = _orientation(p2, q2, p1)
    o4 = _orientation(p2, q2, q1)

    if o1 != o2 and o3 != o4:
        return True

    if o1 == 0 and _on_segment(p1, p2, q1):
        return True
    if o2 == 0 and _on_segment(p1, q2, q1):
        return True
    if o3 == 0 and _on_segment(p2, p1, q2):
        return True
    if o4 == 0 and _on_segment(p2, q1, q2):
        return True

    return False


def validate_no_self_intersection(closed_points: list[CoordinatePoint]) -> None:
    """Check for self-intersecting segments.

    [F-22] The algorithm is O(n²).  validate_points() already enforces
    MAX_VERTICES so this function is implicitly protected against DoS.
    """
    if len(closed_points) < 4:
        return

    segment_count = len(closed_points) - 1
    for i in range(segment_count):
        a1 = closed_points[i]
        a2 = closed_points[i + 1]
        for j in range(i + 1, segment_count):
            if j == i + 1:
                continue
            if i == 0 and j == segment_count - 1:
                continue

            b1 = closed_points[j]
            b2 = closed_points[j + 1]
            if _segments_intersect(a1, a2, b1, b2):
                raise ValueError(
                    "Poligono invalido: segmentos com auto-intersecao detectada."
                )
