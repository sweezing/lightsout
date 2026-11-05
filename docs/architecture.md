# Architecture

Lights Out runs as six containers behind one port. The browser only ever talks
to `http://localhost:8080`; nginx routes each path to the right service, so the
frontend needs no backend URL and there is no CORS setup.

```
                         http://localhost:8080
                                  │
                           ┌──────┴──────┐
                           │    proxy    │  nginx
                           └──┬───┬───┬──┘
             /  (pages, JS)   │   │   │  /api/  /ws/  /admin/  /static/
          ┌───────────────────┘   │   └──────────────────────┐
   ┌──────┴──────┐        /media/ │                   ┌──────┴──────┐
   │  frontend   │        (images)│                   │   backend   │  Django + DRF + Channels
   │  Next.js    │                │                   │   (daphne)  │  HTTP API + WebSocket
   └─────────────┘                │                   └──┬───────┬──┘
                                  │                      │       │
                           media volume ◄────────────────┘       │ pub/sub by canvas region
                                                         │       │
                                                  ┌──────┴──┐ ┌──┴─────┐
                                                  │   db    │ │ redis  │
                                                  │Postgres │ │        │
                                                  └────┬────┘ └────────┘
                                                       │
                                                ┌──────┴──────┐
                                                │   worker    │  hourly: 30-day purge,
                                                └─────────────┘  rate-limit cleanup
```

| Service | Image / code | Job |
|---|---|---|
| `proxy` | `nginx:1.27-alpine`, `nginx/nginx.conf` | Single entry point, WebSocket upgrade, serves uploaded images |
| `frontend` | `frontend/` (Next.js 15, React 19, TypeScript) | Canvas, composer, nightly prompt, report and support UI |
| `backend` | `backend/` (Django 5.1, DRF, Channels 4, daphne) | REST API, WebSocket, moderation pipeline, admin review queue |
| `worker` | same image as backend | `run_maintenance` loop: purge removed cards after 30 days, drop old rate-limit rows |
| `db` | `postgres:16-alpine` | Cards, prompts, reports, moderation log. GiST index for viewport queries |
| `redis` | `redis:7-alpine` | Channels layer: fan-out of new cards to readers by canvas region |

## Backend apps and owners

Owners follow Table 1 of the proposal.

| App | Feature | Owner |
|---|---|---|
| `apps/cards` | F1 Anonymous Card Posting: model, create endpoint, rate limit, image cleaning | Kirill Bautin |
| `apps/canvas` | F2 Shared Spatial Canvas: bounding-box viewport query, GiST index, benchmark | Rustem Imangazin |
| `apps/prompts` | F3 Nightly Prompt: prompt bank, local-time window, rotation | Rustem Imangazin |
| `apps/realtime` | F4 Live Card Delivery: WebSocket consumer, region tiles, broadcast | Kirill Bautin |
| `apps/moderation` | F5 Moderation and Safety: screening, reports, review queue, retention | Danila Oleinikov |
| `apps/core` | Health check, `seed`, `wait_for_db`, `run_maintenance` | Kirill Bautin |

## Frontend modules

| File | Purpose | Owner |
|---|---|---|
| `components/FeedView.tsx` | Default Pinterest-style feed: masonry columns, infinite scroll, "Just now" block for live cards | Danila Oleinikov |
| `components/CanvasView.tsx` | Pan, pinch and wheel zoom, dots below 0.5x, tap to place | Rustem Imangazin |
| `components/CardView.tsx` | Card rendering and the one-tap report menu | Danila Oleinikov |
| `components/Composer.tsx` | Write step: 280-character limit, optional photo | Danila Oleinikov |
| `components/PromptBanner.tsx` | Tonight's question | Rustem Imangazin |
| `components/SupportPanel.tsx` | Support resources (crisis path and footer link) | Danila Oleinikov |
| `components/LightsOut.tsx` | Page state: camera, card store, write, place and post flow | Danila Oleinikov |
| `lib/live.ts` | WebSocket client, reconnect, 30 s polling fallback | Kirill Bautin |
| `lib/camera.ts` | World to screen math, zoom around a point | Rustem Imangazin |
| `lib/api.ts`, `lib/session.ts` | API calls and the anonymous session token | Kirill Bautin |

## Key flows

**Posting a card (F1 + F5 + F4).** The composer collects text and an optional
photo. The reader taps the canvas to place it. `POST /api/cards/` checks the
session token against the rate limit, validates length and coordinates,
re-encodes the image without metadata, and runs `moderation.pipeline.screen()`
before anything is saved as published. Published cards go to Redis on commit and
reach every reader whose viewport overlaps that region of the canvas.

**Reading, feed (default).** The page asks for a shuffled page of all cards
(`GET /api/cards/feed/`, seed chosen per visit), packs them into 2 to 5
columns by estimated height, and loads the next page as the reader nears the
bottom. Live cards go into a "Just now" block above the columns so the layout
never shifts under the reader. The reader can switch to the canvas at any time;
the choice is remembered on the device.

**Reading, canvas (F2).** The page asks for the visible rectangle plus a 60% margin
(`GET /api/canvas/viewport/`), keeps cards near the view in memory, and only
refetches when the camera leaves the loaded area.

**Live updates (F4).** One WebSocket per tab. The client sends its viewport
after every pan or zoom; the server joins the matching region groups. If the
socket drops, the client retries within 3 s and refetches the viewport. If it
stays down for 8 s, the client polls every 30 s until the socket returns.

## Spatial index without PostGIS

The proposal allowed "GiST or PostGIS". The project uses PostgreSQL's built-in
`point` type with a partial GiST index (`cards/migrations/0002_spatial_index.py`)
so the stack runs on the stock `postgres:16-alpine` image on both Intel and
Apple Silicon machines. Measured with `manage.py bench_viewport`: p95 about 5 ms
at 10,000 cards against the 300 ms target.
