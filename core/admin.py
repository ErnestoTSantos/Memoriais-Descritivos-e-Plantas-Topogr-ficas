from django.contrib import admin

from core.models import Artifact, ProcessRun, Project, Vertex

admin.site.register(Project)
admin.site.register(ProcessRun)
admin.site.register(Vertex)
admin.site.register(Artifact)
