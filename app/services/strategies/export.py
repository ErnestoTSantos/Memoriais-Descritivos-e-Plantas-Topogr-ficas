from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from app.models.schemas import CoordinatePoint
from app.services.reports import export_docx, export_dxf, export_pdf


@dataclass(frozen=True)
class ExportPayload:
    property_name: str
    points: list[CoordinatePoint]
    memorial_text: str
    output_dir: Path
    slug: str
    token: str


@dataclass(frozen=True)
class ExportResult:
    path: Path
    media_type: str


class FileExportStrategy(ABC):
    @abstractmethod
    def export(self, payload: ExportPayload) -> ExportResult:
        raise NotImplementedError


class PdfExportStrategy(FileExportStrategy):
    def export(self, payload: ExportPayload) -> ExportResult:
        path = payload.output_dir / f"memorial_{payload.slug}_{payload.token}.pdf"
        export_pdf(
            path,
            f"Memorial Descritivo - {payload.property_name}",
            payload.memorial_text,
            payload.points,
        )
        return ExportResult(path=path, media_type="application/pdf")


class DocxExportStrategy(FileExportStrategy):
    def export(self, payload: ExportPayload) -> ExportResult:
        path = payload.output_dir / f"memorial_{payload.slug}_{payload.token}.docx"
        export_docx(
            path,
            f"Memorial Descritivo - {payload.property_name}",
            payload.memorial_text,
            payload.points,
        )
        return ExportResult(
            path=path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )


class DxfExportStrategy(FileExportStrategy):
    def export(self, payload: ExportPayload) -> ExportResult:
        path = payload.output_dir / f"planta_{payload.slug}_{payload.token}.dxf"
        export_dxf(path, payload.points, f"Planta Baixa - {payload.property_name}")
        return ExportResult(path=path, media_type="application/dxf")


class DwgExportStrategy(FileExportStrategy):
    """DWG is a proprietary Autodesk binary format that cannot be produced by
    simply renaming a DXF file.  Doing so yields a corrupted, unreadable file.

    This strategy intentionally raises an explicit error instead of silently
    returning an invalid file.  Callers should use DxfExportStrategy for
    CAD-compatible output or integrate a real ODA/LibreCAD converter here.
    """

    def export(self, payload: ExportPayload) -> ExportResult:
        raise NotImplementedError(
            "Exportacao DWG nao esta disponivel. "
            "Use o formato DXF para compatibilidade com software CAD. "
            "Para DWG real e necessario um conversor externo (ex: ODA File Converter)."
        )


class ExportStrategyFactory:
    def __init__(self) -> None:
        self._pdf_strategy = PdfExportStrategy()
        self._docx_strategy = DocxExportStrategy()
        self._dxf_strategy = DxfExportStrategy()
        # DWG requests are routed to a clear ValueError by for_output_format().

    def for_output_format(self, output_format: str) -> FileExportStrategy:
        fmt = output_format.lower()
        if fmt == "pdf":
            return self._pdf_strategy
        if fmt == "docx":
            return self._docx_strategy
        if fmt == "dxf":
            return self._dxf_strategy
        if fmt == "dwg":
            raise ValueError(
                "Exportacao DWG nao esta disponivel. "
                "Use o formato DXF — ambos sao compatíveis com AutoCAD e LibreCAD."
            )
        raise ValueError("Formato invalido. Use: pdf, docx ou dxf.")
