"""Measure viewport query latency against the Table 3 target
(p95 <= 300 ms with 10,000 cards in the database).

    docker compose exec backend python manage.py bench_viewport

Inserts temporary benchmark cards, times the same query the API runs, then
deletes them again.
"""
import random
import time

from django.core.management.base import BaseCommand

from apps.canvas.spatial import BBox, cards_in_bbox
from apps.cards.models import Card

TAG = "__bench__"

class Command(BaseCommand):
    help = "Benchmark the viewport query (Feature 2)."

    def add_arguments(self, parser):
        parser.add_argument("--cards", type=int, default=10_000)
        parser.add_argument("--queries", type=int, default=300)

    def handle(self, *args, cards, queries, **options):
        rng = random.Random(498)
        existing = Card.objects.count()
        to_add = max(0, cards - existing)
        Card.objects.bulk_create(
            (Card(text=TAG, x=rng.uniform(-30_000, 30_000), y=rng.uniform(-30_000, 30_000)) for _ in range(to_add)),
            batch_size=2_000,
        )
        try:
            timings = []
            for _ in range(queries):
                cx, cy = rng.uniform(-28_000, 28_000), rng.uniform(-28_000, 28_000)
                half = rng.choice([800, 2_000, 6_000])
                t = time.perf_counter()
                list(cards_in_bbox(BBox(cx - half, cy - half, cx + half, cy + half)))
                timings.append((time.perf_counter() - t) * 1000)
            timings.sort()
            p50 = timings[len(timings) // 2]
            p95 = timings[int(len(timings) * 0.95) - 1]
            verdict = "PASS" if p95 <= 300 else "FAIL"
            self.stdout.write(
                f"{Card.objects.count()} cards, {queries} queries: p50 {p50:.1f} ms, p95 {p95:.1f} ms "
                f"(target <= 300 ms) {verdict}"
            )
        finally:
            Card.objects.filter(text=TAG).delete()
