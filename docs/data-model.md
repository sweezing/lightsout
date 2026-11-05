# Data model

```
prompts_prompt                 cards_card                         moderation_report
───────────────                ─────────────────────────          ──────────────────
id            PK               id            UUID PK      ◄────── card_id  FK
text     ≤60 chars             text          1-280 chars          reason   enum
position      unique           image         path, nullable       resolved bool
is_active                      x, y          float                created_at
created_at        ◄─────────── prompt_id     FK, nullable
                               status        enum                 moderation_moderationdecision
                               is_seed       bool                 ─────────────────────────────
                               created_at                 ◄────── card_id    FK
                               status_changed_at                  source     auto|reports|moderator
                                                                  outcome    card status
cards_ratelimitevent  (not linked to anything)                    reason, scores (json)
────────────────────                                              moderator  FK auth_user (team member)
session_hash  HMAC-SHA256 of the browser token                    created_at
created_at
```

## Card status

| Status | Visible | How it gets there |
|---|---|---|
| `published` | yes | Passed automatic screening, or approved by a moderator |
| `pending_review` | no | 3 open reports, or 1 "I'm worried" report |
| `withheld` | no | Crisis indicator at posting time; poster was shown support resources |
| `rejected` | no | Threat, harassment, personal information or a link at posting time |
| `removed` | no | Moderator decision |

Hidden cards (`withheld`, `rejected`, `removed`) are deleted for good 30 days
after their last status change, together with their reports and log rows and
any uploaded image (`purge_removed_cards`, run hourly by the worker).

## Privacy rules enforced by the schema

* `cards_card` has no user, session, email or IP column. Tests check this
  (`apps/cards/tests/test_posting.py`).
* The rate limit stores a keyed hash of the browser token in a separate table
  that has no link to cards, and rows older than one hour are deleted.
* `moderation_report` stores no reporter identity.
* The only person ever recorded is the team moderator on a manual decision.
* Uploaded images get a random file name and are re-encoded so EXIF data
  (GPS, camera model, time) is dropped.

## Indexes

* `cards_card (status, created_at)` for "latest published" queries.
* Partial GiST index `cards_card_published_point_gist` on `point(x, y)` where
  `status = 'published'` for viewport queries.
