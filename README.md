# Lights Out

An anonymous shared canvas for the thoughts that keep you up at night.
No usernames, no followers, no likes, no ranking: just short cards on one
continuous canvas that everyone awake can wander through.

ISTA 498 Senior Capstone, University of Arizona, Fall 2026, Group 4.
Kirill Bautin (back end), Danila Oleinikov (front end), Rustem Imangazin (full stack).

## Run it

You need **Docker Desktop** (Mac, Windows) or Docker Engine with Compose v2.24+
(Linux). Nothing else: no Python, Node or Postgres on your machine.

```bash
cp .env.example .env        # optional, every value has a default
docker compose up --build
```

The first build takes a few minutes. When the logs settle, open:

| What | URL |
|---|---|
| The canvas | http://localhost:8080 |
| Moderation queue | http://localhost:8080/admin/ (login `moderator` / `lights-out-local`, from `.env`) |
| API health | http://localhost:8080/api/health/ |

On first start the database is seeded with 200 starter cards and 60 nightly
prompts, so the canvas is never empty.

Stop with `Ctrl+C`, or `docker compose down`. Wipe all data with
`docker compose down -v`. Port 8080 taken? Set `APP_PORT=8090` in `.env`.

## Use it

* The **Feed** (default) shows every card in Pinterest-style columns, in a new
  random order each visit. Scroll down for more; new cards appear under
  **Just now** at the top. **Canvas** (top right) switches to the shared
  canvas, and the choice is remembered.
* **Drag** to move around, **pinch**, **ctrl + scroll** or the **− / +** buttons
  to zoom. Below half size the cards turn into small lights.
* **Write a card**. In the feed, **Post it** publishes straight away. On the
  canvas you then **tap where it should live** (or "Put it in the middle").
  Either way it appears for everyone else without a refresh.
* **Tonight's question** shows between 21:00 and 05:00 your time. Answering it
  just writes a normal card.
* **⋯ on a card** reports it in one tap.
* Keyboard: arrows move, `+` / `-` zoom, `0` back to centre, `N` new card.

## What's inside

```
backend/            Django 5.1 + DRF + Channels (daphne), Python 3.12
  apps/cards/         F1 anonymous posting, rate limit, image cleaning
  apps/canvas/        F2 viewport (bounding-box) queries, GiST index, benchmark
  apps/prompts/       F3 nightly prompt bank and local-time window
  apps/realtime/      F4 WebSocket live delivery by canvas region
  apps/moderation/    F5 screening, reports, review queue, 30-day retention
  apps/core/          health, seed, wait_for_db, worker loop
frontend/           Next.js 15 + React 19 + TypeScript
  components/         canvas, card, composer, prompt, support panel
  lib/                API client, camera math, live client, session token
seed/               200 starter cards, 60 prompts
nginx/              single entry point on :8080
docs/               architecture, API contract, data model, moderation policy,
                    requirements traceability
tools/              WebSocket load test
.github/workflows/  CI: backend tests on Postgres, frontend build, compose smoke test
```

Feature owners and design notes: [docs/architecture.md](docs/architecture.md).
Which proposal requirement lives where and how it is checked:
[docs/requirements-traceability.md](docs/requirements-traceability.md).

## Develop and test

Everything runs inside the containers:

```bash
docker compose exec backend python manage.py test apps          # 51 backend tests
docker compose exec backend python manage.py bench_viewport      # Table 3 latency target
docker compose exec backend python manage.py seed                # reload seed content
docker compose exec backend python manage.py createsuperuser     # another moderator
docker compose logs -f backend                                   # follow the API logs
pip install websockets && python tools/ws_load_test.py           # Table 5: 100 live readers
```

Changed front-end or back-end code? `docker compose up --build` again.

## Privacy by design

A card stores no account, name, email, IP address or session. The rate limit
uses a hashed browser token in a separate table, deleted after an hour. Photo
metadata (GPS, camera, time) is stripped on upload. Reports store no reporter.
Details: [docs/data-model.md](docs/data-model.md).
