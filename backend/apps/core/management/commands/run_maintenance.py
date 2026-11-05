import time

from django.core.management import call_command
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Worker loop: run periodic cleanup jobs every --interval seconds."

    def add_arguments(self, parser):
        parser.add_argument("--interval", type=int, default=3600)
        parser.add_argument("--once", action="store_true")

    def handle(self, *args, interval, once, **options):
        while True:
            call_command("purge_removed_cards")
            call_command("purge_rate_limit_events")
            if once:
                return
            time.sleep(interval)
