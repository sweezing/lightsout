# Moderation and safety policy

Owner: Danila Oleinikov. Applies to Feature 5 and every public deployment.
Status: **draft for team and advisor review.**

## Why moderation is part of the MVP

Anonymity without moderation is how every product in our competitor scan
failed, and the canvas is used late at night, when people can be at their most
vulnerable. So screening runs before a card is published, not after.

## What the canvas does not allow

| Rule | Example | Automatic outcome |
|---|---|---|
| Threats or harassment aimed at someone | "kill yourself" | Rejected, not published |
| Personal information about anyone | email, phone number, social handle | Rejected |
| Links | `www…`, `http…` | Rejected (spam and doxxing) |
| Content suggesting the writer may be at risk | "I want to die" | Withheld, poster sees support resources |

Sad, lonely, angry or uncomfortable thoughts are **allowed**. That is what the
product is for. The filter targets harm and risk, not mood.

## The pipeline

1. **Automatic screening, 100% of cards, before publication.**
   `apps/moderation/pipeline.py`, `screen()`. A crisis indicator wins over every
   other rule, so a person in distress always sees support, never a rejection.
2. **One-tap reports.** No account, no explanation required. Three open
   reports hide the card for review. One "I'm worried about this person" report
   hides it immediately.
3. **Manual review queue.** Django admin, `/admin/cards/card/?status__exact=pending_review`.
   The "Waiting" column turns red after 24 hours. Actions: *Approve and
   publish* or *Remove*.
4. **Retention.** Withheld, rejected and removed cards are kept 30 days for
   appeal and audit, then deleted permanently.
5. **Decision log.** Every automatic and manual outcome is written to
   `ModerationDecision`, with matched terms for automatic decisions. No poster
   identity is stored anywhere.

## Review rota

Target: every card in the queue has a decision within 24 hours.

| Day | Reviewer |
|---|---|
| Mon, Thu | Danila |
| Tue, Fri | Rustem |
| Wed, Sat, Sun | Kirill |

TODO(team): confirm the rota and add moderator accounts
(`docker compose exec backend python manage.py createsuperuser`).

## Word lists

Defaults are in `apps/moderation/wordlists.py`. Extra terms go one per line in
`apps/moderation/wordlists/blocked.txt` and `crisis.txt`. Changes go through a
pull request reviewed by a second team member.

## Known gaps (be honest about these in reports)

* The "classifier" is currently a transparent keyword heuristic behind a
  `Classifier` interface. TODO: add a trained text classifier that runs
  locally. Card text must not be sent to a third-party AI service (proposal
  Appendix C).
* **Photos are not screened automatically.** They are covered only by reports
  and the review queue. TODO: decide before public launch whether to hold
  cards with photos for review, or drop photos from the public MVP.
* Keyword matching is English only.
* Support resources (`apps/moderation/resources.py`) must be re-verified
  before every public deployment.
