from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.cards.models import Card

HIDDEN = [Card.Status.REMOVED, Card.Status.REJECTED, Card.Status.WITHHELD]

class Command(BaseCommand):
    help = "Permanently delete cards that have been off the canvas for the retention period (Table 6: 30 days)."

    def handle(self, *args, **options):
        days = settings.LIGHTS_OUT["REMOVED_RETENTION_DAYS"]
        cutoff = timezone.now() - timedelta(days=days)
        doomed = Card.objects.filter(status__in=HIDDEN, status_changed_at__lt=cutoff)
        count = 0
        for card in doomed.iterator():
            if card.image:
                card.image.delete(save=False)
            count += 1
        doomed.delete()  #reports and decision log rows cascade
        self.stdout.write(f"cards purged after {days} days: {count}")
