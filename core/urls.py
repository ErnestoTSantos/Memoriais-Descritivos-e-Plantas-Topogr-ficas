from django.urls import path

from core import views

urlpatterns = [
    path("", views.home, name="home"),
    path("api/process", views.process_coordinates, name="process_coordinates"),
    path("api/export/<str:output_format>", views.export_file, name="export_file"),
    path("api/artifacts", views.list_artifacts, name="list_artifacts"),
]
