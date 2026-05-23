from __future__ import annotations

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.serializers import ProcessingRequestSerializer, ProcessingResponseSerializer
from core.services import process_topographic_request


class ProcessCoordinatesView(APIView):
    """Process planimetric traverse or irradiation payloads."""

    serializer_class = ProcessingRequestSerializer
    response_serializer_class = ProcessingResponseSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            payload = process_topographic_request(
                serializer.build_project_data(),
                serializer.build_processing_input(),
            )
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        response_serializer = self.response_serializer_class(payload)
        return Response(response_serializer.data)
