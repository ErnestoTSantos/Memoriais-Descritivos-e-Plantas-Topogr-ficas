from __future__ import annotations

import csv
import os
import tempfile
import zipfile
from abc import ABC, abstractmethod
from io import StringIO
from pathlib import Path

import shapefile

from app.models.schemas import CoordinatePoint, IrradiationObservation
from app.services.angles import parse_azimuth

POSSIBLE_X_COLUMNS = {"x", "e", "este", "east", "coord_x", "utm_x", "longitude"}
POSSIBLE_Y_COLUMNS = {"y", "n", "norte", "north", "coord_y", "utm_y", "latitude"}
POSSIBLE_VERTEX_COLUMNS = {"vertex", "vertice", "id", "ponto", "codigo", "name"}
POSSIBLE_AZIMUTH_COLUMNS = {"azimute", "azimuth", "azimuth_deg", "angulo", "bearing"}
POSSIBLE_DISTANCE_COLUMNS = {"distancia", "distance", "distance_m", "comprimento"}
POSSIBLE_STATION_X_COLUMNS = {
    "estacao_x",
    "station_x",
    "origem_x",
    "origin_x",
    "setup_x",
}
POSSIBLE_STATION_Y_COLUMNS = {
    "estacao_y",
    "station_y",
    "origem_y",
    "origin_y",
    "setup_y",
}
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
# 512 KB covers roughly 10,000 pasted vertices with room for delimiters.
MAX_TEXT_BYTES = 512 * 1024
ALLOWED_ZIP_SUFFIXES = {".shp", ".shx", ".dbf", ".prj", ".cpg"}
# shapeType codes: 5=Polygon, 15=PolygonZ, 25=PolygonM
ACCEPTED_SHAPE_TYPES = {5, 15, 25}


def _to_float(value: str | None, field_name: str, line: str) -> float:
    if value is None:
        raise ValueError(f"Campo '{field_name}' ausente na linha: '{line}'")

    cleaned = value.strip().replace(",", ".")

    if cleaned == "":
        raise ValueError(f"Campo '{field_name}' vazio na linha: '{line}'")

    try:
        return float(cleaned)
    except ValueError:
        raise ValueError(
            f"Valor inválido para '{field_name}': '{value}' na linha: '{line}'"
        )


def _normalize_header(value: str) -> str:
    return value.strip().lower()


def _safe_get(row: dict, key: str | None) -> str:
    if not key:
        return ""
    return (row.get(key) or "").strip()


def _decode_text(raw: str | bytes) -> str:
    if isinstance(raw, str):
        if len(raw.encode("utf-8")) > MAX_TEXT_BYTES:
            raise ValueError(
                f"Texto muito grande ({len(raw)} chars). "
                f"Limite: {MAX_TEXT_BYTES // 1024} KB."
            )
        return raw
    if len(raw) > MAX_UPLOAD_BYTES:
        raise ValueError(
            f"Arquivo muito grande ({len(raw) // 1024} KB). "
            f"Limite: {MAX_UPLOAD_BYTES // (1024 * 1024)} MB."
        )
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Encoding invalido. Envie o arquivo em UTF-8.") from exc


def _validate_zip_member(member: zipfile.ZipInfo) -> None:
    member_path = Path(member.filename)
    if member_path.is_absolute() or ".." in member_path.parts:
        raise ValueError("ZIP invalido: caminho interno inseguro.")

    if member.is_dir():
        return

    if member.file_size > MAX_UPLOAD_BYTES:
        raise ValueError("ZIP invalido: arquivo interno muito grande.")

    if member_path.suffix.lower() not in ALLOWED_ZIP_SUFFIXES:
        raise ValueError("ZIP invalido: contem arquivo nao permitido para shapefile.")


class CoordinateParsingStrategy(ABC):
    @abstractmethod
    def parse(self, raw: str | bytes) -> list[CoordinatePoint]:
        raise NotImplementedError


class IrradiationParsingStrategy(ABC):
    @abstractmethod
    def parse(self, raw: str | bytes) -> list[IrradiationObservation]:
        raise NotImplementedError


class TextCoordinatesParsingStrategy(CoordinateParsingStrategy):
    def parse(self, raw: str | bytes) -> list[CoordinatePoint]:
        text = _decode_text(raw)

        points: list[CoordinatePoint] = []
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        for idx, line in enumerate(lines, start=1):
            normalized = line.replace(";", ",").replace("\t", ",")
            chunks = [c.strip() for c in normalized.split(",") if c.strip()]

            if len(chunks) == 2:
                vertex = f"V-{idx:03d}"
                x_val, y_val = chunks

            elif len(chunks) >= 3:
                vertex, x_val, y_val = chunks[:3]

            else:
                raise ValueError(f"Linha inválida na coordenada: '{line}'")

            points.append(
                CoordinatePoint(
                    vertex=vertex,
                    x=_to_float(x_val, "X", line),
                    y=_to_float(y_val, "Y", line),
                )
            )

        if len(points) < 3:
            raise ValueError("É necessário ao menos 3 pontos para formar um polígono.")

        return points


class CsvTxtParsingStrategy(CoordinateParsingStrategy):
    def __init__(self, fallback_strategy: CoordinateParsingStrategy | None = None):
        self._fallback = fallback_strategy or TextCoordinatesParsingStrategy()

    def parse(self, raw: str | bytes) -> list[CoordinatePoint]:
        text = _decode_text(raw)

        try:
            dialect = csv.Sniffer().sniff(text[:3000], delimiters=",;\t")
            delimiter = dialect.delimiter
        except csv.Error:
            delimiter = ","

        reader = csv.DictReader(StringIO(text), delimiter=delimiter)

        if not reader.fieldnames:
            return self._fallback.parse(text)

        headers = {_normalize_header(h): h for h in reader.fieldnames if h}

        x_key = next((headers[h] for h in headers if h in POSSIBLE_X_COLUMNS), None)
        y_key = next((headers[h] for h in headers if h in POSSIBLE_Y_COLUMNS), None)
        v_key = next(
            (headers[h] for h in headers if h in POSSIBLE_VERTEX_COLUMNS), None
        )

        if not x_key or not y_key:
            return self._fallback.parse(text)

        points: list[CoordinatePoint] = []

        invalid_lines: list[str] = []

        for idx, row in enumerate(reader, start=1):
            line = str(row)

            x_raw = _safe_get(row, x_key)
            y_raw = _safe_get(row, y_key)

            if not x_raw or not y_raw:
                invalid_lines.append(
                    f"  Linha {idx}: campo(s) X ou Y ausente(s) — {line}"
                )
                continue

            vertex = _safe_get(row, v_key) or f"V-{idx:03d}"

            points.append(
                CoordinatePoint(
                    vertex=vertex,
                    x=_to_float(x_raw, "X", line),
                    y=_to_float(y_raw, "Y", line),
                )
            )

        if invalid_lines:
            raise ValueError(
                f"{len(invalid_lines)} linha(s) invalida(s) no CSV:\n"
                + "\n".join(invalid_lines)
            )

        if not points:
            raise ValueError("Nenhuma coordenada válida encontrada no arquivo.")

        return points


class TextIrradiationParsingStrategy(IrradiationParsingStrategy):
    def parse(self, raw: str | bytes) -> list[IrradiationObservation]:
        text = _decode_text(raw)

        observations: list[IrradiationObservation] = []
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        for idx, line in enumerate(lines, start=1):
            normalized = line.replace(";", ",").replace("\t", ",")
            chunks = [c.strip() for c in normalized.split(",") if c.strip()]

            if len(chunks) < 2:
                raise ValueError(f"Linha inválida na irradiação: '{line}'")

            if len(chunks) == 2:
                vertex = f"V-{idx:03d}"
                az, dist = chunks
                sx = sy = None

            elif len(chunks) == 3:
                vertex, az, dist = chunks
                sx = sy = None

            elif len(chunks) == 4:
                vertex, _, az, dist = chunks
                sx = sy = None

            else:
                vertex, sx_raw, sy_raw, az, dist = chunks[:5]
                sx = _to_float(sx_raw, "Estação X", line)
                sy = _to_float(sy_raw, "Estação Y", line)

            observations.append(
                IrradiationObservation(
                    vertex=vertex,
                    azimuth_deg=parse_azimuth(az),
                    distance_m=_to_float(dist, "Distância", line),
                    station_x=sx,
                    station_y=sy,
                )
            )

        if not observations:
            raise ValueError("Nenhuma observação válida encontrada.")

        return observations


class CsvTxtIrradiationParsingStrategy(IrradiationParsingStrategy):
    def __init__(self, fallback_strategy: IrradiationParsingStrategy | None = None):
        self._fallback = fallback_strategy or TextIrradiationParsingStrategy()

    def parse(self, raw: str | bytes) -> list[IrradiationObservation]:
        text = _decode_text(raw)

        try:
            delimiter = csv.Sniffer().sniff(text[:3000], delimiters=",;\t").delimiter
        except csv.Error:
            delimiter = ","

        reader = csv.DictReader(StringIO(text), delimiter=delimiter)

        if not reader.fieldnames:
            return self._fallback.parse(text)

        headers = {_normalize_header(h): h for h in reader.fieldnames if h}

        az_key = next(
            (headers[h] for h in headers if h in POSSIBLE_AZIMUTH_COLUMNS), None
        )
        dist_key = next(
            (headers[h] for h in headers if h in POSSIBLE_DISTANCE_COLUMNS), None
        )
        sx_key = next(
            (headers[h] for h in headers if h in POSSIBLE_STATION_X_COLUMNS), None
        )
        sy_key = next(
            (headers[h] for h in headers if h in POSSIBLE_STATION_Y_COLUMNS), None
        )
        v_key = next(
            (headers[h] for h in headers if h in POSSIBLE_VERTEX_COLUMNS), None
        )

        if not az_key or not dist_key:
            return self._fallback.parse(text)

        observations: list[IrradiationObservation] = []

        for idx, row in enumerate(reader, start=1):
            line = str(row)

            az = _safe_get(row, az_key)
            dist = _safe_get(row, dist_key)

            if not az or not dist:
                continue

            vertex = _safe_get(row, v_key) or f"V-{idx:03d}"

            sx_raw = _safe_get(row, sx_key)
            sy_raw = _safe_get(row, sy_key)

            observations.append(
                IrradiationObservation(
                    vertex=vertex,
                    azimuth_deg=parse_azimuth(az),
                    distance_m=_to_float(dist, "Distância", line),
                    station_x=_to_float(sx_raw, "Estação X", line) if sx_raw else None,
                    station_y=_to_float(sy_raw, "Estação Y", line) if sy_raw else None,
                )
            )

        if not observations:
            raise ValueError("Nenhuma observação válida encontrada no CSV.")

        return observations


class ShapefileZipParsingStrategy(CoordinateParsingStrategy):
    def parse(self, raw: str | bytes) -> list[CoordinatePoint]:
        if isinstance(raw, str):
            raise ValueError("Shapefile requer binário.")
        if len(raw) > MAX_UPLOAD_BYTES:
            raise ValueError("Arquivo muito grande para processamento.")

        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = os.path.join(temp_dir, "input.zip")

            with open(zip_path, "wb") as f:
                f.write(raw)

            try:
                archive = zipfile.ZipFile(zip_path, "r")
            except zipfile.BadZipFile as exc:
                raise ValueError("Shapefile corrompido ou ZIP invalido.") from exc

            with archive as z:
                for member in z.infolist():
                    _validate_zip_member(member)
                z.extractall(temp_dir)

            shp_files = [f for f in os.listdir(temp_dir) if f.endswith(".shp")]

            if not shp_files:
                raise ValueError("ZIP não contém .shp")

            try:
                sf_reader = shapefile.Reader(os.path.join(temp_dir, shp_files[0]))
                shapes = sf_reader.shapes()
            except Exception as exc:
                raise ValueError("Shapefile corrompido ou geometria ilegivel.") from exc

            if not shapes:
                raise ValueError("Shapefile vazio.")

            shape_type = sf_reader.shapeType
            if shape_type not in ACCEPTED_SHAPE_TYPES:
                raise ValueError(
                    f"Tipo de geometria nao suportado: shapeType={shape_type}. "
                    "Envie apenas shapefiles do tipo Polygon (5), PolygonZ (15) "
                    "ou PolygonM (25)."
                )

            pts = shapes[0].points

            if len(pts) < 3:
                raise ValueError("Geometria inválida: menos de 3 pontos.")

            # Shapefiles include an explicit closing point; downstream validation
            # expects distinct polygon vertices.
            if len(pts) >= 2:
                first_pt = pts[0]
                last_pt = pts[-1]
                if (
                    abs(float(first_pt[0]) - float(last_pt[0])) <= 1e-9
                    and abs(float(first_pt[1]) - float(last_pt[1])) <= 1e-9
                ):
                    pts = pts[:-1]

            if len(pts) < 3:
                raise ValueError(
                    "Geometria inválida: menos de 3 vértices distintos após remover "
                    "o ponto de fechamento."
                )

            return [
                CoordinatePoint(vertex=f"V-{i:03d}", x=float(x), y=float(y))
                for i, (x, y) in enumerate(pts, start=1)
            ]


class ParsingStrategyFactory:
    def __init__(self):
        self.text = TextCoordinatesParsingStrategy()
        self.csv = CsvTxtParsingStrategy(self.text)
        self.shp = ShapefileZipParsingStrategy()
        self.irr_text = TextIrradiationParsingStrategy()
        self.irr_csv = CsvTxtIrradiationParsingStrategy(self.irr_text)

    def for_text(self):
        return self.text

    def for_upload_name(self, name: str):
        name = name.lower()
        if name.endswith(".zip"):
            return self.shp
        if name.endswith((".csv", ".txt")):
            return self.csv
        raise ValueError("Formato não suportado.")

    def for_irradiation_text(self):
        return self.irr_text

    def for_irradiation_upload_name(self, name: str):
        name = name.lower()
        if name.endswith((".csv", ".txt")):
            return self.irr_csv
        raise ValueError("Formato não suportado para irradiação.")
