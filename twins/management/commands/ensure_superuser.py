from django.core.management.base import BaseCommand
from django.conf import settings
import os


class Command(BaseCommand):
    help = "Ensure a Django superuser exists (username/password from env)"

    def handle(self, *args, **options):
        from django.contrib.auth import get_user_model
        User = get_user_model()

        username = os.getenv('DJANGO_SUPERUSER_USERNAME', '')
        password = os.getenv('DJANGO_SUPERUSER_PASSWORD', '')
        email = os.getenv('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')

        if not username or not password:
            self.stdout.write("DJANGO_SUPERUSER_USERNAME or DJANGO_SUPERUSER_PASSWORD not set; skipping superuser creation")
            return

        u, created = User.objects.get_or_create(username=username, defaults={'email': email})
        u.email = email
        u.is_staff = True
        u.is_superuser = True
        u.set_password(password)
        u.save()

        if created:
            self.stdout.write(self.style.SUCCESS(f"Superuser '{username}' created"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Superuser '{username}' ensured/updated"))
