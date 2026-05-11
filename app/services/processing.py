from __future__ import annotations

from dataclasses import dataclass
import re

from app.models.schemas import CoordinatePoint, IrradiationObservation, SegmentInfo
from app.services.geometry import (
    build_segments,
    closure_error,
    ensure_closed,
    polygon_area,
    polygon_perimeter,
    validate_no_self_intersection,
    validate_points,
)
from app.services.irradiation import irradiation_to_points
from app.services.reports import generate_memorial_text


# =========================
# DATA CLASSES
# =========================

@dataclass(frozen=True)
class Station:
    name: str
    x: float
    y: float


@dataclass(frozen=True)
class ProjectData:
    property_name: str
    owner_name: str
    municipality: str
    state: str
    datum: str
    coordinate_system: str
    measurement_mode: str

    stations: list[Station]

    irradiation_angle_error_seconds: float | None
    angle_error_limit_seconds: float | None
    closure_tolerance_m: float | None


@dataclass(frozen=True)
class ProcessingResult:
    points: list[CoordinatePoint]
    segments: list[SegmentInfo]
    area_m2: float
    perimeter_m: float
    closure_error_m: float
    memorial_text: str


# =========================
# PARSERS
# =========================

def parse_angle(value) -> float:
    if isinstance(value, (int, float)):
        return float(value) % 360

    text = str(value).strip().replace(",", ".")

    gms_pattern = r"(\d+)[°\s]+(\d+)[\'\s]+(\d+(?:\.\d+)?)"
    match = re.search(gms_pattern, text)

    if match:
        g, m, s = match.groups()
        return (float(g) + float(m)/60 + float(s)/3600) % 360

    return float(text) % 360


def validate_irradiation_input(observations: list[IrradiationObservation]) -> None:
    for obs in observations:
        if float(obs.distance_m) <= 0:
            raise ValueError(f"Distância inválida para o ponto {obs.vertex}")


# =========================
# BUILD PROJECT DATA
# =========================

def build_project_data(raw):

    def parse_float(v):
        if v is None:
            return None
        text = str(v).strip()
        if text == "":
            return None
        return float(text.replace(",", "."))

    angle_error = parse_float(raw.get("irradiation_angle_error_seconds"))
    angle_limit = parse_float(raw.get("angle_error_limit_seconds"))
    closure_tolerance = parse_float(raw.get("closure_tolerance_m") or 0.05)

    if angle_limit is not None and angle_limit <= 0:
        raise ValueError("O limite do erro angular deve ser maior que zero.")

    if angle_error is not None and angle_limit is not None and abs(angle_error) > angle_limit:
        raise ValueError(
            f"Erro angular informado ({angle_error:.2f} s) excede o limite de {angle_limit:.2f} s."
        )

    if closure_tolerance is not None and closure_tolerance <= 0:
        raise ValueError("A tolerancia de fechamento deve ser maior que zero.")

    stations = []

    # estação principal
    if raw.get("irradiation_origin_x") and raw.get("irradiation_origin_y"):
        stations.append(
            Station(
                name="E1",
                x=parse_float(raw["irradiation_origin_x"]),
                y=parse_float(raw["irradiation_origin_y"]),
            )
        )

    return ProjectData(
        property_name=raw.get("property_name", "Imovel"),
        owner_name=raw.get("owner_name", "Proprietario"),
        municipality=raw.get("municipality", "Municipio"),
        state=(raw.get("state") or "UF").upper()[:2],
        datum=raw.get("datum", "SIRGAS2000"),
        coordinate_system=raw.get("coordinate_system", "UTM"),
        measurement_mode="irradiacao" if "irradiacao" in str(raw.get("measurement_mode", "")).lower() else "ponto_a_ponto",
        stations=stations,
        irradiation_angle_error_seconds=angle_error,
        angle_error_limit_seconds=angle_limit,
        closure_tolerance_m=closure_tolerance,
    )


# =========================
# MAIN
# =========================

def process_coordinates(points, project_data):

    if project_data.measurement_mode == "irradiacao":

        if not project_data.stations:
            raise ValueError("Nenhuma estação informada")

        validate_irradiation_input(points)
        default_station = project_data.stations[0]

        points = irradiation_to_points(
            points,
            origin_x=default_station.x,
            origin_y=default_station.y,
            angle_error_seconds=project_data.irradiation_angle_error_seconds or 0,
        )

    validate_points(points)

    closed_points = ensure_closed(points)

    validate_no_self_intersection(closed_points)

    area = polygon_area(closed_points)
    if area <= 0:
        raise ValueError("Poligono invalido: area deve ser maior que zero.")

    segments = build_segments(
        closed_points,
        angle_error_seconds=project_data.irradiation_angle_error_seconds or 0.0,
    )

    perimeter = polygon_perimeter(closed_points)
    misclosure = closure_error(closed_points)

    if project_data.closure_tolerance_m is not None:
        if misclosure > project_data.closure_tolerance_m:
            raise ValueError(
                f"Erro de fechamento ({misclosure:.4f} m) excede tolerância de {project_data.closure_tolerance_m} m"
            )

    memorial_text = generate_memorial_text(
        property_name=project_data.property_name,
        owner_name=project_data.owner_name,
        municipality=project_data.municipality,
        state=project_data.state,
        datum=project_data.datum,
        coordinate_system=project_data.coordinate_system,
        measurement_mode=project_data.measurement_mode,
        irradiation_origin_x=project_data.stations[0].x if project_data.stations else None,
        irradiation_origin_y=project_data.stations[0].y if project_data.stations else None,
        irradiation_angle_error_seconds=project_data.irradiation_angle_error_seconds,
        area_m2=area,
        perimeter_m=perimeter,
        segments=segments,
    )

    return ProcessingResult(
        points=closed_points,
        segments=segments,
        area_m2=area,
        perimeter_m=perimeter,
        closure_error_m=misclosure,
        memorial_text=memorial_text,
    )
