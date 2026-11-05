"""Which prompt is live, computed from the reader's local time.

No scheduler is needed: the active prompt is a pure function of the date of
the night the reader is in, so every server and every reader agree on it.

Table 4 rules:
  * exactly one prompt is active at a time;
  * the window is 21:00-05:00 in the reader's local time;
  * outside the window the previous night's prompt stays visible.
"""
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from django.conf import settings

from .models import Prompt

EPOCH = date(2026, 1, 1)

@dataclass
class ActivePrompt:
    prompt: Prompt | None
    night_of: date
    in_window: bool

def local_now(tz_offset_minutes: int, now: datetime | None = None) -> datetime:
    """Reader's wall-clock time. `tz_offset_minutes` is minutes east of UTC."""
    now = now or datetime.now(timezone.utc)
    return now.astimezone(timezone.utc) + timedelta(minutes=tz_offset_minutes)

def night_for(local: datetime) -> tuple[date, bool]:
    """Return (night_of, in_window) for a local wall-clock time.

    A night is named after the evening it starts on, so 02:00 on the 5th
    belongs to the night of the 4th. Between 05:00 and 21:00 we are outside
    the window and the night that just ended is still shown.
    """
    start = settings.LIGHTS_OUT["PROMPT_WINDOW_START_HOUR"]
    end = settings.LIGHTS_OUT["PROMPT_WINDOW_END_HOUR"]
    hour = local.hour
    if hour >= start:
        return local.date(), True
    if hour < end:
        return local.date() - timedelta(days=1), True
    return local.date() - timedelta(days=1), False

def prompt_for_night(night_of: date) -> Prompt | None:
    bank = list(Prompt.objects.filter(is_active=True).order_by("position"))
    if not bank:
        return None
    return bank[(night_of - EPOCH).days % len(bank)]

def active_prompt(tz_offset_minutes: int = 0, now: datetime | None = None) -> ActivePrompt:
    night_of, in_window = night_for(local_now(tz_offset_minutes, now))
    return ActivePrompt(prompt_for_night(night_of), night_of, in_window)
