"""Feature 5 - Moderation and Safety Pipeline (Table 6)."""
import uuid
from datetime import timedelta

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.cards.models import Card
from apps.moderation import pipeline
from apps.moderation.models import ModerationDecision, Report

LAYER = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}

@override_settings(CHANNEL_LAYERS=LAYER)
class ScreeningTests(TestCase):
    def post(self, text):
        return APIClient().post(
            "/api/cards/", {"text": text, "x": 0, "y": 0}, format="json",
            HTTP_X_SESSION_TOKEN=uuid.uuid4().hex,
        )

    def test_every_card_is_screened_and_logged(self):
        self.post("just a normal night")
        self.post("another one")
        self.assertEqual(ModerationDecision.objects.filter(source="auto").count(), Card.objects.count())

    def test_crisis_card_is_withheld_and_resources_shown(self):
        r = self.post("honestly i want to die tonight")
        self.assertEqual(r.status_code, 202)
        body = r.json()
        self.assertEqual(body["status"], "withheld")
        self.assertTrue(body["resources"])
        self.assertEqual(Card.objects.get().status, Card.Status.WITHHELD)

    def test_crisis_wins_over_rejection(self):
        r = self.post("i want to die, email me at a@b.com")
        self.assertEqual(r.json()["status"], "withheld")

    def test_threats_are_rejected(self):
        r = self.post("kill yourself")
        self.assertEqual(r.status_code, 422)
        self.assertEqual(Card.objects.get().status, Card.Status.REJECTED)

    def test_personal_info_is_rejected(self):
        for text in ("write me at someone@example.com", "call +7 777 123 45 67", "see www.example.com"):
            self.assertEqual(self.post(text).json()["status"], "rejected", text)

    def test_ordinary_sad_card_is_published(self):
        self.assertEqual(self.post("i feel lonely tonight and that's okay").status_code, 201)

    def test_screen_is_pure_function(self):
        self.assertEqual(pipeline.screen("goodnight").card_status, Card.Status.PUBLISHED)

@override_settings(CHANNEL_LAYERS=LAYER)
class ReportingTests(TestCase):
    def setUp(self):
        self.card = Card.objects.create(text="something", x=0, y=0)
        self.url = f"/api/cards/{self.card.id}/report/"

    def test_one_tap_report_no_account(self):
        r = APIClient().post(self.url, {}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(Report.objects.count(), 1)

    def test_report_stores_no_reporter_identity(self):
        names = {f.name for f in Report._meta.get_fields()}
        self.assertTrue(names.isdisjoint({"user", "ip", "session", "session_hash", "reporter"}))

    def test_threshold_hides_card_for_review(self):
        for _ in range(3):
            APIClient().post(self.url, {"reason": "harmful"}, format="json")
        self.card.refresh_from_db()
        self.assertEqual(self.card.status, Card.Status.PENDING_REVIEW)

    def test_worried_report_goes_straight_to_queue(self):
        APIClient().post(self.url, {"reason": "worried"}, format="json")
        self.card.refresh_from_db()
        self.assertEqual(self.card.status, Card.Status.PENDING_REVIEW)

    def test_moderator_approve_and_remove(self):
        pipeline.remove(self.card)
        self.assertEqual(self.card.status, Card.Status.REMOVED)
        pipeline.approve(self.card)
        self.assertEqual(self.card.status, Card.Status.PUBLISHED)
        self.assertEqual(self.card.decisions.filter(source="moderator").count(), 2)

class RetentionTests(TestCase):
    def test_removed_cards_purged_after_30_days(self):
        old = Card.objects.create(text="old", x=0, y=0, status=Card.Status.REMOVED)
        fresh = Card.objects.create(text="fresh", x=0, y=0, status=Card.Status.REMOVED)
        live = Card.objects.create(text="live", x=0, y=0)
        Card.objects.filter(id__in=[old.id, live.id]).update(
            status_changed_at=timezone.now() - timedelta(days=31)
        )
        call_command("purge_removed_cards", stdout=open("/dev/null", "w"))
        remaining = set(Card.objects.values_list("text", flat=True))
        self.assertEqual(remaining, {"fresh", "live"})
