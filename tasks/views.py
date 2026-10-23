from rest_framework import viewsets

from .models import Task
from .serializers import TaskSerializer


class TaskViewSet(viewsets.ModelViewSet):
    """CRUD de tareas. Los permisos (GET libre, resto autenticado) vienen de settings."""

    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]  # sin PUT
