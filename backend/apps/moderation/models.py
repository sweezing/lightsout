"""Moderation records (Table 6, "Data required").

Neither model stores anything about who posted or who reported: no session,
no IP, no user. That is the proposal's rule: "no poster identity is recorded
in either".
"""
from django.conf import settings
from django.db import models

class Report(models.Model):
    class Reason(models.TextChoices):
        HARMFUL = "harmful", "Harmful or abusive"
        PERSONAL_INFO = "personal_info", "Shares someone's personal information"
        SPAM = "spam", "Spam"
        WORRIED = "worried", "I'm worried about the person who wrote this"
        OTHER = "other", "Something else"

    card = models.ForeignKey("cards.Card", on_delete=models.CASCADE, related_name="reports")
    reason = models.CharField(max_length=20, choices=Reason.choices, default=Reason.OTHER)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Report {self.reason} on {self.card_id}"

class ModerationDecision(models.Model):
    """Append-only log of every moderation outcome, automatic or manual."""

    class Source(models.TextChoices):
        AUTO = "auto", "Automatic screening"
        REPORTS = "reports", "Report threshold"
        MODERATOR = "moderator", "Moderator"

    card = models.ForeignKey("cards.Card", on_delete=models.CASCADE, related_name="decisions")
    source = models.CharField(max_length=20, choices=Source.choices)
    outcome = models.CharField(max_length=20)  #mirrors card.status values
    reason = models.CharField(max_length=200, blank=True)
    scores = models.JSONField(default=dict, blank=True)
    moderator = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        help_text="Team member who made a manual decision (never the poster).",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.source}: {self.outcome} ({self.card_id})"
