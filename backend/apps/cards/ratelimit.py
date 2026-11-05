"""Feature 1: 5 posts per hour per anonymous session."""
import hashlib
import hmac
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import RateLimitEvent

HEADER = "HTTP_X_SESSION_TOKEN"
WINDOW = timedelta(hours=1)

def session_hash(request) -> str | None:
    token = request.META.get(HEADER, "").strip()
    if not (16 <= len(token) <= 128):
        return None
    #keyed hash: the raw token never reaches the database.
    return hmac.new(settings.SECRET_KEY.encode(), token.encode(), hashlib.sha256).hexdigest()

def is_limited(h: str) -> bool:
    since = timezone.now() - WINDOW
    used = RateLimitEvent.objects.filter(session_hash=h, created_at__gte=since).count()
    return used >= settings.LIGHTS_OUT["RATE_LIMIT_PER_HOUR"]

def record(h: str) -> None:
    RateLimitEvent.objects.create(session_hash=h)
