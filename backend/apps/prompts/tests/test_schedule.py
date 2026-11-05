"""Feature 3 - Nightly Prompt (Table 4)."""
import uuid
from datetime import date, datetime, timedelta, timezone

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.cards.models import Card
from apps.prompts.models import Prompt
from apps.prompts.schedule import active_prompt, night_for

def utc(*a):
    return datetime(*a, tzinfo=timezone.utc)

class WindowTests(TestCase):
    def test_window_21_to_05(self):
        self.assertEqual(night_for(datetime(2026, 11, 4, 21, 0)), (date(2026, 11, 4), True))
        self.assertEqual(night_for(datetime(2026, 11, 5, 2, 0)), (date(2026, 11, 4), True))
        self.assertEqual(night_for(datetime(2026, 11, 5, 4, 59)), (date(2026, 11, 4), True))

    def test_outside_window_keeps_previous_prompt(self):
        #14:00 on the 5th: the night of the 4th is still shown, flagged out of window.
        self.assertEqual(night_for(datetime(2026, 11, 5, 14, 0)), (date(2026, 11, 4), False))

class RotationTests(TestCase):
    def setUp(self):
        for i in range(1, 61):
            Prompt.objects.create(position=i, text=f"Question {i}?")

    def test_exactly_one_prompt_and_no_repeat_for_60_nights(self):
        seen = set()
        for day in range(60):
            p = active_prompt(0, utc(2026, 1, 1, 22, 0) + timedelta(days=day))
            seen.add(p.prompt.id)
        self.assertEqual(len(seen), 60)

    def test_uses_reader_local_time(self):
        now = utc(2026, 11, 1, 17, 0)  #17:00 UTC
        almaty = active_prompt(5 * 60, now) #22:00 local -> in window
        tucson = active_prompt(-7 * 60, now) #10:00 local -> out of window
        self.assertTrue(almaty.in_window)
        self.assertFalse(tucson.in_window)

    def test_api(self):
        r = APIClient().get("/api/prompt/current/", {"tz_offset": 300})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(set(r.json()), {"id", "text", "night_of", "in_window"})

@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
class AnswerTests(TestCase):
    def test_answer_is_plain_card_linked_internally(self):
        Prompt.objects.create(position=1, text="What kept you up?")
        #sweep every time zone: some readers are inside the window, some outside.
        client = APIClient()
        for offset in range(-12 * 60, 14 * 60 + 1, 60):
            client.post(
                "/api/cards/", {"text": f"answer {offset}", "x": 0, "y": 0, "tz_offset": offset},
                format="json", HTTP_X_SESSION_TOKEN=uuid.uuid4().hex,
            )
        self.assertTrue(Card.objects.filter(prompt__isnull=False).exists())
        self.assertTrue(Card.objects.filter(prompt__isnull=True).exists())
        card = client.get("/api/cards/").json()[0]
        self.assertNotIn("prompt", card)
