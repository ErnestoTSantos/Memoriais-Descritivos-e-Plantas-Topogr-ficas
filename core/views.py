from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from django.contrib.gis.geos import Point
from django.core.files.storage import default_storage
from django.db import transaction
from django.http import FileResponse, HttpRequest, JsonResponse
from django.shortcuts import render
from django.utils.text import slugify
from django.views.decorators.csrf import ensure_csrf_cookie

from app.models.schemas import CoordinatePoint
from app.services.processing import (
    ProjectData,
    build_project_data,
    process_coordinates as process_polygon,
)
from app.services.strategies.export import ExportPayload, ExportStrategyFactory
from app.services.strategies.parsing import ParsingStrategyFactory
from core.models import Artifact, ProcessRun, Project, Vertex

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

PARSING_FACTORY = ParsingStrategyFactory()
EXPORT_FACTORY = ExportStrategyFactory()


@ensure_csrf_cookie
def home(request: HttpRequest):
    return render(request, "index.html")


# =========================
# EXTRAÇÃO DE DADOS
# =========================

def _extract_project_data(request: HttpRequest) -> ProjectData:
    raw_data = {
        "property_name": request.POST.get("property_name", ""),
        "owner_name": request.POST.get("owner_name", ""),
        "municipality": request.POST.get("municipality", ""),
        "state": request.POST.get("state", ""),
        "datum": request.POST.get("datum", ""),
        "coordinate_system": request.POST.get("coordinate_system", ""),
        "measurement_mode": request.POST.get("measurement_mode", ""),
        "irradiation_origin_x": request.POST.get("irradiation_origin_x", ""),
        "irradiation_origin_y": request.POST.get("irradiation_origin_y", ""),
        "irradiation_angle_error_seconds": request.POST.get("irradiation_angle_error_seconds", ""),
        "angle_error_limit_seconds": request.POST.get("angle_error_limit_seconds", ""),
        "closure_tolerance_m": request.POST.get("closure_tolerance_m", ""),  # 🔥 NOVO
    }
    return build_project_data(raw_data)


# =========================
# PERSISTÊNCIA
# =========================

def _save_run(
    project_data: ProjectData,
    points: list[CoordinatePoint],
    area: float,
    perimeter: float,
    misclosure: float,
) -> ProcessRun:

    project = Project.objects.create(
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
        angle_error_limit_seconds=project_data.angle_error_limit_seconds,
    )

    run = ProcessRun.objects.create(
        project=project,
        area_m2=area,
        perimeter_m=perimeter,
        closure_error_m=misclosure,
    )

    for idx, point in enumerate(points[:-1], start=1):
        Vertex.objects.create(
            process_run=run,
            vertex_code=getattr(point, "vertex", "") or getattr(point, "name", ""),
            x_coord=point.x,
            y_coord=point.y,
            seq=idx,
            geom=Point(point.x, point.y, srid=31983),
        )

    return run


# =========================
# PROCESSAMENTO PRINCIPAL
# =========================

def process_coordinates(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return JsonResponse({"detail": "Metodo invalido."}, status=405)

    try:
        file = request.FILES.get("file")
        project_data = _extract_project_data(request)

        # =====================
        # PARSING (SEM CONVERSÃO!)
        # =====================

        if project_data.measurement_mode == "irradiacao":

            if file and getattr(file, "name", ""):
                raw = file.read()
                parsing_strategy = PARSING_FACTORY.for_irradiation_upload_name(file.name)
                points = parsing_strategy.parse(raw)

            else:
                coordinates_text = request.POST.get("coordinates_text", "")
                if not coordinates_text.strip():
                    return JsonResponse(
                        {"detail": "Informe observacoes de irradiacao por arquivo ou texto."},
                        status=400,
                    )

                points = PARSING_FACTORY.for_irradiation_text().parse(coordinates_text)

            # 🔥 VALIDAÇÃO DE ESTAÇÃO
            if not project_data.stations:
                return JsonResponse(
                    {"detail": "Informe pelo menos uma estação para irradiação."},
                    status=400,
                )

        else:
            if file and getattr(file, "name", ""):
                raw = file.read()
                parsing_strategy = PARSING_FACTORY.for_upload_name(file.name)
                points = parsing_strategy.parse(raw)

            else:
                coordinates_text = request.POST.get("coordinates_text", "")
                if not coordinates_text.strip():
                    return JsonResponse(
                        {"detail": "Informe coordenadas por arquivo ou texto."},
                        status=400,
                    )

                points = PARSING_FACTORY.for_text().parse(coordinates_text)

        # =====================
        # PROCESSAMENTO CENTRAL
        # =====================

        result = process_polygon(points, project_data)

        with transaction.atomic():
            _save_run(
                project_data,
                result.points,
                result.area_m2,
                result.perimeter_m,
                result.closure_error_m,
            )

        payload = {
            "points": [point.model_dump() for point in result.points],
            "area_m2": result.area_m2,
            "perimeter_m": result.perimeter_m,
            "closure_error_m": result.closure_error_m,
            "segments": [segment.model_dump() for segment in result.segments],
            "memorial_text": result.memorial_text,
            "measurement_mode": project_data.measurement_mode,
            "stations": [
                {"name": s.name, "x": s.x, "y": s.y}
                for s in getattr(project_data, "stations", [])
            ],
            "irradiation_angle_error_seconds": project_data.irradiation_angle_error_seconds,
            "angle_error_limit_seconds": project_data.angle_error_limit_seconds,
            "closure_tolerance_m": getattr(project_data, "closure_tolerance_m", None),
        }

        return JsonResponse(payload)

    except Exception as exc:
        return JsonResponse({"detail": str(exc)}, status=400)


# =========================
# EXPORTAÇÃO
# =========================

def _store_artifact(path: Path, output_format: str, run: ProcessRun) -> None:
    with path.open("rb") as fp:
        storage_key = default_storage.save(f"exports/{path.name}", fp)

    try:
        file_url = default_storage.url(storage_key)
    except Exception:
        file_url = ""

    Artifact.objects.create(
        process_run=run,
        output_format=output_format,
        storage_key=storage_key,
        file_url=file_url,
    )


def export_file(request: HttpRequest, output_format: str):
    if request.method != "POST":
        return JsonResponse({"detail": "Metodo invalido."}, status=405)

    try:
        data = json.loads(request.body.decode("utf-8"))

        raw_points = [CoordinatePoint(**point) for point in data.get("points", [])]

        project_data = build_project_data(
            {
                "property_name": data.get("property_name", ""),
                "owner_name": data.get("owner_name", ""),
                "municipality": data.get("municipality", ""),
                "state": data.get("state", ""),
                "datum": data.get("datum", ""),
                "coordinate_system": data.get("coordinate_system", ""),
                "measurement_mode": data.get("measurement_mode", ""),
                "irradiation_origin_x": data.get("irradiation_origin_x", ""),
                "irradiation_origin_y": data.get("irradiation_origin_y", ""),
                "irradiation_angle_error_seconds": data.get("irradiation_angle_error_seconds", ""),
                "angle_error_limit_seconds": data.get("angle_error_limit_seconds", ""),
                "closure_tolerance_m": data.get("closure_tolerance_m", ""),
            }
        )

        result = process_polygon(raw_points, project_data)

        slug = slugify(project_data.property_name) or "imovel"
        token = uuid4().hex[:8]

        export_payload = ExportPayload(
            property_name=project_data.property_name,
            points=result.points[:-1],
            memorial_text=result.memorial_text,
            output_dir=OUTPUT_DIR,
            slug=slug,
            token=token,
        )

        export_strategy = EXPORT_FACTORY.for_output_format(output_format)
        export_result = export_strategy.export(export_payload)

        with transaction.atomic():
            run = _save_run(
                project_data,
                result.points,
                result.area_m2,
                result.perimeter_m,
                result.closure_error_m,
            )
            _store_artifact(export_result.path, output_format, run)

        return FileResponse(
            export_result.path.open("rb"),
            as_attachment=True,
            filename=export_result.path.name,
            content_type=export_result.media_type,
        )

    except Exception as exc:
        return JsonResponse({"detail": str(exc)}, status=400)


# =========================
# LISTAGEM
# =========================

def list_artifacts(request: HttpRequest) -> JsonResponse:
    artifacts = (
        Artifact.objects
        .select_related("process_run", "process_run__project")
        .order_by("-created_at")[:100]
    )

    payload = [
        {
            "id": artifact.id,
            "format": artifact.output_format,
            "storage_key": artifact.storage_key,
            "file_url": artifact.file_url,
            "created_at": artifact.created_at.isoformat(),
            "project": artifact.process_run.project.property_name,
        }
        for artifact in artifacts
    ]

    return JsonResponse({"artifacts": payload})
