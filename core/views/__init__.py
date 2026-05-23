from .exports import ArtifactViewSet, ExportFileView
from .home import HomeView
from .planimetric import ProcessCoordinatesView

home = HomeView.as_view()
process_coordinates = ProcessCoordinatesView.as_view()
export_file = ExportFileView.as_view()
list_artifacts = ArtifactViewSet.as_view({"get": "list"})

__all__ = [
    "ArtifactViewSet",
    "ExportFileView",
    "HomeView",
    "ProcessCoordinatesView",
    "export_file",
    "home",
    "list_artifacts",
    "process_coordinates",
]
