"""The moderation and safety pipeline (Feature 5).

    screen(text)          automatic check, runs before publication (100% of cards)
    register_report(card) one-tap report; N reports -> hidden for manual review
    approve / remove      moderator decisions from the admin review queue

Order of checks matters: a crisis indicator wins over everything else, so a
person in distress is always shown support resources rather than a rejection.
"""
from dataclasses import dataclass

from django.conf import settings
from django.db import transaction

from apps.cards.models import Card
from apps.realtime.broadcast import broadcast_card_created, broadcast_card_hidden

from .classifier import Scores, get_classifier
from .models import ModerationDecision, Report

THRESHOLD = 0.5

@dataclass
class Verdict:
    card_status: str
    reason: str
    scores: Scores

def screen(text: str) -> Verdict:
    scores = get_classifier().score(text)
    if scores.crisis >= THRESHOLD:
        return Verdict(Card.Status.WITHHELD, "crisis indicator", scores)
    if scores.harmful >= THRESHOLD:
        return Verdict(Card.Status.REJECTED, "threat or harassment", scores)
    if scores.personal_info >= THRESHOLD:
        return Verdict(Card.Status.REJECTED, "personal information or link", scores)
    return Verdict(Card.Status.PUBLISHED, "passed automatic screening", scores)

def log_auto_decision(card: Card, verdict: Verdict) -> None:
    ModerationDecision.objects.create(
        card=card,
        source=ModerationDecision.Source.AUTO,
        outcome=verdict.card_status,
        reason=verdict.reason,
        scores=verdict.scores.as_dict(),
    )

@transaction.atomic
def register_report(card: Card, reason: str) -> Report:
    report = Report.objects.create(card=card, reason=reason)
    open_reports = card.reports.filter(resolved=False).count()
    #a "worried" report goes straight to the queue: the 24 h response target
    #matters most when someone may be at risk.
    urgent = reason == Report.Reason.WORRIED
    if card.status == Card.Status.PUBLISHED and (
        urgent or open_reports >= settings.LIGHTS_OUT["REPORTS_BEFORE_REVIEW"]
    ):
        card.status = Card.Status.PENDING_REVIEW
        card.save(update_fields=["status", "status_changed_at"])
        ModerationDecision.objects.create(
            card=card,
            source=ModerationDecision.Source.REPORTS,
            outcome=card.status,
            reason="urgent report" if urgent else f"{open_reports} open reports",
        )
        transaction.on_commit(lambda: broadcast_card_hidden(card))
    return report

@transaction.atomic
def approve(card: Card, moderator=None, reason: str = "") -> None:
    card.status = Card.Status.PUBLISHED
    card.save(update_fields=["status", "status_changed_at"])
    card.reports.update(resolved=True)
    ModerationDecision.objects.create(
        card=card, source=ModerationDecision.Source.MODERATOR, outcome=card.status,
        reason=reason or "approved after review", moderator=moderator,
    )
    transaction.on_commit(lambda: broadcast_card_created(card))

@transaction.atomic
def remove(card: Card, moderator=None, reason: str = "") -> None:
    was_visible = card.is_visible
    card.status = Card.Status.REMOVED
    card.save(update_fields=["status", "status_changed_at"])
    card.reports.update(resolved=True)
    ModerationDecision.objects.create(
        card=card, source=ModerationDecision.Source.MODERATOR, outcome=card.status,
        reason=reason or "removed after review", moderator=moderator,
    )
    if was_visible:
        transaction.on_commit(lambda: broadcast_card_hidden(card))
