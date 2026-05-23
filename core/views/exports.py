from __future__ import annotations

from django.http import FileResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.views import APIView

from core.models import Artifact
from core.serializers import ArtifactSerializer, ExportRequestSerializer
from core.services import export_project_file


class ExportFileView(APIView):
    serializer_class = ExportRequestSerializer

    def post(self, request, output_format: str, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            exported_file = export_project_file(
                output_format=output_format,
                project_data=serializer.build_project_data(),
                points=serializer.build_points(),
                memorial_text=serializer.validated_data.get("memorial_text", ""),
                planimetric_table=serializer.validated_data.get("planimetric_table"),
            )
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return FileResponse(
            exported_file.path.open("rb"),
            as_attachment=True,
            filename=exported_file.path.name,
            content_type=exported_file.media_type,
        )


class ArtifactViewSet(ReadOnlyModelViewSet):
    serializer_class = ArtifactSerializer

    def get_queryset(self):
        return Artifact.objects.select_related(
            "process_run",
            "process_run__project",
        ).order_by("-created_at")[:100]

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response({"artifacts": serializer.data})
