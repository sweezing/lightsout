# Seed content

Loaded automatically on the first `docker compose up` (when the database is
empty) by `python manage.py seed --if-empty`. To reload by hand:

```bash
docker compose exec backend python manage.py seed
```

| File | What | Proposal reference |
|---|---|---|
| `cards.json` | 200 starter cards, placed on a spiral around the canvas origin | Milestone "Seed content loaded (minimum 200 cards)"; cold-start problem from the user research |
| `prompts.json` | 60 nightly questions, each 60 characters or less | Table 4: "Prompt bank at launch: 60", "Prompt length: max 60 chars" |

Seed cards are flagged `is_seed=True` in the database, so they can be filtered
out of any usage numbers and replaced later without touching real posts.

**Before launch:** the team reviews and rewrites both files in its own voice.
They are draft placeholders, not user data, and must not be presented as real
posts from real people in the poster, pitch or any write-up.
