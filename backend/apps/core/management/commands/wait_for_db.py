import time

from django.core.management.base import BaseCommand
from django.db import connection
from django.db.utils import OperationalError

class Command(BaseCommand):
    help = "Block until the database accepts connections (used by the container entrypoint)."

    def add_arguments(self, parser):
        parser.add_argument("--timeout", type=int, default=60)

    def handle(self, *args, timeout, **options):
        deadline = time.monotonic() + timeout
        while True:
            try:
                connection.ensure_connection()
                self.stdout.write("database ready")
                return
            except OperationalError:
                if time.monotonic() > deadline:
                    raise
                time.sleep(1)
