import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    """Crea (o actualiza) el usuario de demostración con credenciales del entorno."""

    help = "Crea el usuario demo usando DEMO_USER y DEMO_PASSWORD"

    def handle(self, *args, **options):
        username = os.environ.get("DEMO_USER", "demo")
        password = os.environ.get("DEMO_PASSWORD")
        if not password:
            raise CommandError("Define la variable de entorno DEMO_PASSWORD")
        user, _ = get_user_model().objects.get_or_create(username=username)
        user.set_password(password)  # se guarda con hash, nunca en texto plano
        user.save()
        self.stdout.write(self.style.SUCCESS(f"Usuario '{username}' listo"))
