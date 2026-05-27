from django.core.management.base import BaseCommand
from django.conf import settings
import requests
import sys


class Command(BaseCommand):
    help = "Ensure a Middts user exists and that the client can obtain a token"

    def handle(self, *args, **options):
        username = getattr(settings, 'MIDDTS_API_USERNAME', 'middts')
        password = getattr(settings, 'MIDDTS_API_PASSWORD', 'middts123')
        base = getattr(settings, 'MIDDTS_API_URL', 'http://localhost:8000/api').rstrip('/')

        token_url = f"{base}/core/token/"
        users_url = f"{base}/core/users/"

        self.stdout.write(f"[ensure_middts_user] trying to obtain token for {username}...")
        try:
            resp = requests.post(f"{token_url}?username={username}&password={password}", timeout=10)
        except Exception as e:
            self.stderr.write(f"token request failed: {e}")
            resp = None

        if resp is not None and resp.status_code == 200:
            self.stdout.write(self.style.SUCCESS("Token obtained successfully"))
            return

        self.stdout.write("Token request failed; attempting to create user on Middts...")
        payload = {
            "username": username,
            "password": password,
            "email": f"{username}@example.com",
            "first_name": "Middts",
            "last_name": "Client",
            "is_staff": False,
            "role": "member",
        }
        try:
            r = requests.post(users_url, json=payload, timeout=10)
            if r.status_code in (200, 201):
                self.stdout.write(self.style.SUCCESS(f"User '{username}' created on Middts (status {r.status_code})"))
            else:
                self.stderr.write(f"User creation returned status {r.status_code}: {r.text}")
        except Exception as e:
            self.stderr.write(f"User creation request failed: {e}")

        # try token again
        try:
            resp2 = requests.post(f"{token_url}?username={username}&password={password}", timeout=10)
            if resp2.status_code == 200:
                self.stdout.write(self.style.SUCCESS("Token obtained after user creation"))
                return
            else:
                self.stderr.write(f"Token still not available: {resp2.status_code} {resp2.text}")
                sys.exit(1)
        except Exception as e:
            self.stderr.write(f"Second token request failed: {e}")
            sys.exit(1)
