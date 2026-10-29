import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = ("Creates the /admin administrator if there is none (DJANGO_SUPERUSER_USERNAME / _PASSWORD / _EMAIL; "
            "admin / admin by default). If there is one already, it changes nothing.")

    def handle(self, *args, **options):
        User = get_user_model()
        if User.objects.filter(is_superuser=True).exists():
            return
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME") or "admin"
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD") or "admin"
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL") or ""
        User.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(self.style.WARNING(
            f"Created the administrator “{username}”. Change its password if this machine is not only yours."))
