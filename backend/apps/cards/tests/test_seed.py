from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from apps.cards.models import Card
from apps.moderation.pipeline import screen
from apps.prompts.models import Prompt

class SeedTests(TestCase):
    def test_seed_loads_200_cards_and_60_prompts(self):
        call_command("seed", stdout=StringIO())
        self.assertGreaterEqual(Card.objects.filter(is_seed=True).count(), 200)
        self.assertEqual(Prompt.objects.count(), 60)
        self.assertTrue(all(len(p.text) <= 60 for p in Prompt.objects.all()))

    def test_seed_if_empty_is_idempotent(self):
        call_command("seed", "--if-empty", stdout=StringIO())
        call_command("seed", "--if-empty", stdout=StringIO())
        self.assertEqual(Card.objects.count(), 200)

    def test_seed_cards_pass_moderation(self):
        call_command("seed", stdout=StringIO())
        for card in Card.objects.all():
            self.assertEqual(screen(card.text).card_status, Card.Status.PUBLISHED, card.text)
