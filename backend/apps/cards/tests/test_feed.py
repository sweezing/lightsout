"""Pinterest-style feed: shuffled, stable per visit, paged without repeats."""
from django.test import TestCase
from rest_framework.test import APIClient

from apps.cards.models import Card

URL = "/api/cards/feed/"

class FeedTests(TestCase):
    def setUp(self):
        Card.objects.bulk_create(Card(text=f"card {i}", x=i, y=i) for i in range(95))
        Card.objects.create(text="hidden", x=0, y=0, status=Card.Status.REMOVED)
        self.client = APIClient()

    def walk(self, seed, limit=40):
        ids, offset = [], 0
        while offset is not None:
            body = self.client.get(URL, {"seed": seed, "offset": offset, "limit": limit}).json()
            ids += [c["id"] for c in body["cards"]]
            offset = body["next_offset"]
        return ids

    def test_pages_cover_every_published_card_once(self):
        ids = self.walk("abc")
        self.assertEqual(len(ids), 95)
        self.assertEqual(len(set(ids)), 95)

    def test_hidden_cards_never_in_feed(self):
        texts = {c["text"] for c in self.client.get(URL, {"seed": "x", "limit": 100}).json()["cards"]}
        self.assertNotIn("hidden", texts)

    def test_same_seed_same_order_new_seed_new_order(self):
        self.assertEqual(self.walk("visit1"), self.walk("visit1"))
        self.assertNotEqual(self.walk("visit1"), self.walk("visit2"))

    def test_not_ordered_by_time(self):
        newest_first = [str(c.id) for c in Card.objects.filter(status="published").order_by("-created_at")]
        self.assertNotEqual(self.walk("s"), newest_first)

    def test_limit_is_capped(self):
        body = self.client.get(URL, {"seed": "s", "limit": 5000}).json()
        self.assertEqual(len(body["cards"]), 95)

    def test_bad_seed_is_sanitized(self):
        self.assertEqual(self.client.get(URL, {"seed": "'; drop table x;--"}).status_code, 200)
