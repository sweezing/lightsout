from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.cards.models import RateLimitEvent
from apps.cards.ratelimit import WINDOW

class Command(BaseCommand):
    help = "Delete rate-limit events older than the 1-hour window."

    def handle(self, *args, **options):
        deleted, _ = RateLimitEvent.objects.filter(created_at__lt=timezone.now() - WINDOW).delete()
        self.stdout.write(f"rate-limit events purged: {deleted}")
