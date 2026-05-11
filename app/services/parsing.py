from __future__ import annotations

from app.models.schemas import CoordinatePoint
from app.services.strategies.parsing import ParsingStrategyFactory

_factory = ParsingStrategyFactory()


def parse_text_coordinates(raw_text: str) -> list[CoordinatePoint]:
    return _factory.for_text().parse(raw_text)


def parse_csv_or_txt(content: bytes) -> list[CoordinatePoint]:
    return _factory.for_upload_name("input.csv").parse(content)


def parse_shapefile_zip(content: bytes) -> list[CoordinatePoint]:
    return _factory.for_upload_name("input.zip").parse(content)
