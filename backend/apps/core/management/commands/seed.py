"""Load starter cards and the prompt bank.

Addresses the cold-start problem from the user research: a visitor should
never land on an empty canvas (proposal milestone: minimum 200 seed cards).
"""
import json
import math
import os
import random
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.cards.models import Card
from apps.prompts.models import Prompt

def seed_dir() -> Path:
    return Path(os.environ.get("SEED_DIR", settings.BASE_DIR.parent / "seed"))

def spiral_positions(n: int, spacing: float = 185.0, seed: int = 498):
    """Spread cards outward from the origin with a little jitter.

    A golden-angle spiral keeps the density even, so the first screen a visitor
    sees is full but nothing overlaps.
    """
    rng = random.Random(seed)
    golden = math.pi * (3 - math.sqrt(5))
    for i in range(n):
        r = spacing * math.sqrt(i + 0.5)
        theta = i * golden
        yield (
            round(r * math.cos(theta) + rng.uniform(-25, 25), 1),
            round(r * math.sin(theta) + rng.uniform(-25, 25), 1),
        )

class Command(BaseCommand):
    help = "Load seed cards and nightly prompts from the seed/ directory."

    def add_arguments(self, parser):
        parser.add_argument("--if-empty", action="store_true", help="Skip anything that already has data.")

    @transaction.atomic
    def handle(self, *args, if_empty, **options):
        base = seed_dir()

        prompts = json.loads((base / "prompts.json").read_text(encoding="utf-8"))
        if if_empty and Prompt.objects.exists():
            self.stdout.write("prompts: already present, skipped")
        else:
            for i, text in enumerate(prompts, start=1):
                Prompt.objects.update_or_create(position=i, defaults={"text": text})
            self.stdout.write(f"prompts: {len(prompts)} loaded")

        cards = json.loads((base / "cards.json").read_text(encoding="utf-8"))
        if if_empty and Card.objects.exists():
            self.stdout.write("cards: already present, skipped")
            return
        Card.objects.filter(is_seed=True).delete()
        Card.objects.bulk_create(
            Card(text=text, x=x, y=y, status=Card.Status.PUBLISHED, is_seed=True)
            for text, (x, y) in zip(cards, spiral_positions(len(cards)))
        )
        self.stdout.write(f"cards: {len(cards)} loaded")
