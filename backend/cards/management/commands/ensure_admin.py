import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = ("Crea el administrador de /admin si no hay ninguno (DJANGO_SUPERUSER_USERNAME / _PASSWORD / _EMAIL; "
            "por defecto admin / admin). Si ya hay alguno, no toca nada.")

    def handle(self, *args, **options):
        User = get_user_model()
        if User.objects.filter(is_superuser=True).exists():
            return
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME") or "admin"
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD") or "admin"
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL") or ""
        User.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(self.style.WARNING(
            f"Creado el administrador «{username}». Cambia su contraseña si este equipo no es solo tuyo."))
