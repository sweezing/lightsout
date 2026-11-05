"""Feature 2 - Shared Spatial Canvas (Table 3)."""
from django.db import connection
from django.test import TestCase
from rest_framework.test import APIClient

from apps.cards.models import Card

URL = "/api/canvas/viewport/"

class ViewportTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def get(self, **q):
        return self.client.get(URL, q)

    def test_returns_only_cards_inside_bbox(self):
        Card.objects.create(text="inside", x=100, y=100)
        Card.objects.create(text="outside", x=5000, y=5000)
        r = self.get(min_x=0, min_y=0, max_x=500, max_y=500)
        self.assertEqual([c["text"] for c in r.json()["cards"]], ["inside"])

    def test_inverted_bbox_is_normalized(self):
        Card.objects.create(text="inside", x=100, y=100)
        r = self.get(min_x=500, min_y=500, max_x=0, max_y=0)
        self.assertEqual(len(r.json()["cards"]), 1)

    def test_caps_at_200_cards(self):
        Card.objects.bulk_create(Card(text=f"c{i}", x=i, y=i) for i in range(250))
        r = self.get(min_x=-10, min_y=-10, max_x=1000, max_y=1000)
        self.assertEqual(len(r.json()["cards"]), 200)
        r = self.get(min_x=-10, min_y=-10, max_x=1000, max_y=1000, limit=5000)
        self.assertEqual(len(r.json()["cards"]), 200)

    def test_hidden_cards_never_returned(self):
        for s in (Card.Status.PENDING_REVIEW, Card.Status.WITHHELD, Card.Status.REJECTED, Card.Status.REMOVED):
            Card.objects.create(text=s, x=1, y=1, status=s)
        r = self.get(min_x=0, min_y=0, max_x=10, max_y=10)
        self.assertEqual(r.json()["cards"], [])

    def test_requires_bbox(self):
        self.assertEqual(self.client.get(URL).status_code, 400)

    def test_gist_index_exists_on_postgres(self):
        if connection.vendor != "postgresql":
            self.skipTest("GiST index is PostgreSQL only")
        with connection.cursor() as cur:
            cur.execute("SELECT indexdef FROM pg_indexes WHERE indexname = 'cards_card_published_point_gist'")
            row = cur.fetchone()
        self.assertIsNotNone(row)
        self.assertIn("gist", row[0].lower())
