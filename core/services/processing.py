from __future__ import annotations

from django.db import transaction

from app.services.workflows import (
    ProcessingInput,
    build_result_payload,
    process_project_input,
)
from app.services.processing import ProjectData
from core.persistence import save_process_run


def process_topographic_request(
    project_data: ProjectData,
    processing_input: ProcessingInput,
) -> dict:
    result = process_project_input(project_data, processing_input)

    with transaction.atomic():
        save_process_run(
            project_data,
            result.points,
            result.area_m2,
            result.perimeter_m,
            result.closure_error_m,
            result.planimetric_table.model_dump(),
        )

    return build_result_payload(result, project_data)
