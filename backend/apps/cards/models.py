"""Card data model.

Privacy rule from the proposal (Table 2, "Identity fields stored: 0"):
a card has no account, username, email, IP address or session reference.
The anonymous session token is used only for rate limiting and lives in a
separate table that is never joined to cards (see RateLimitEvent).
"""
import uuid

from django.conf import settings
from django.core.validators import MaxLengthValidator, MinLengthValidator
from django.db import models

LO = settings.LIGHTS_OUT

def card_image_path(instance, filename):
    #random name only; the original filename can identify the poster.
    return f"cards/{uuid.uuid4().hex}.{filename.rsplit('.', 1)[-1].lower()}"

class Card(models.Model):
    class Status(models.TextChoices):
        PUBLISHED = "published", "Published"
        PENDING_REVIEW = "pending_review", "Pending review"
        WITHHELD = "withheld", "Withheld (crisis indicator)"
        REJECTED = "rejected", "Rejected by automatic screening"
        REMOVED = "removed", "Removed by a moderator"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    text = models.TextField(
        validators=[MinLengthValidator(LO["CARD_TEXT_MIN"]), MaxLengthValidator(LO["CARD_TEXT_MAX"])]
    )
    image = models.ImageField(upload_to=card_image_path, blank=True, null=True)

    #position on the shared canvas (feature 2). a GiST index on point(x, y)
    #is created in migration 0002 for bounding-box viewport queries.
    x = models.FloatField()
    y = models.FloatField()

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PUBLISHED, db_index=True)
    is_seed = models.BooleanField(default=False, help_text="Starter card written by the team.")

    #feature 3: which nightly prompt was live when the card was posted.
    #never exposed in the public API, so answers are not labelled as replies.
    prompt = models.ForeignKey(
        "prompts.Prompt", null=True, blank=True, on_delete=models.SET_NULL, related_name="cards"
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    status_changed_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "created_at"])]

    def __str__(self):
        return f"{self.text[:40]} ({self.status})"

    @property
    def is_visible(self):
        return self.status == self.Status.PUBLISHED

class RateLimitEvent(models.Model):
    """One row per accepted post, keyed by a salted hash of the session token.

    Not linked to Card on purpose. Rows older than an hour are useless and are
    deleted by the worker (purge_rate_limit_events).
    """

    session_hash = models.CharField(max_length=64, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
