from __future__ import annotations

import math

from app.models.schemas import CoordinatePoint, SegmentInfo
from app.services.angles import decimal_to_dms

EPSILON = 1e-9


def _format_dms(angle_deg: float) -> str:
    # bearing uses quadrant angle; keep two-digit degrees formatting for readability
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


def ensure_closed(points: list[CoordinatePoint]) -> list[CoordinatePoint]:
    if not points:
        return points
    first = points[0]
    last = points[-1]
    if first.x == last.x and first.y == last.y:
        return points
    closed = points.copy()
    closed.append(CoordinatePoint(vertex=first.vertex, x=first.x, y=first.y))
    return closed


def polygon_area(points: list[CoordinatePoint]) -> float:
    acc = 0.0
    for i in range(len(points) - 1):
        acc += points[i].x * points[i + 1].y - points[i + 1].x * points[i].y
    return abs(acc) / 2.0


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


def build_segments(points: list[CoordinatePoint], angle_error_seconds: float = 0.0) -> list[SegmentInfo]:
    segments: list[SegmentInfo] = []
    for i in range(len(points) - 1):
        start = points[i]
        end = points[i + 1]
        dx = end.x - start.x
        dy = end.y - start.y
        distance = math.hypot(dx, dy)
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
    if len(points) < 3:
        raise ValueError("Sao necessarios ao menos 3 pontos para formar um poligono.")

    canonical_points = points
    if len(points) > 1 and points[0].x == points[-1].x and points[0].y == points[-1].y:
        canonical_points = points[:-1]

    unique_pairs = {(p.x, p.y) for p in canonical_points}
    if len(unique_pairs) < 3:
        raise ValueError("Coordenadas insuficientes ou repetidas para formar um poligono valido.")

    if len(unique_pairs) != len(canonical_points):
        raise ValueError("Coordenadas duplicadas nao sao permitidas no poligono.")

    for point in canonical_points:
        if not math.isfinite(point.x) or not math.isfinite(point.y):
            raise ValueError("Coordenadas invalidas: valores devem ser numericos e finitos.")


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
                raise ValueError("Poligono invalido: segmentos com auto-intersecao detectada.")
