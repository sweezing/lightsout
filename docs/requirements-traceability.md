# Requirements traceability

Every requirement from the proposal (Section 3, Tables 2 to 6) and the
development items from the weekly updates, mapped to where it lives in the
code and how it is checked.

Status: **Done** = implemented and checked. **Partial** = implemented with a
known gap. **Open** = not done yet. Measurements were taken on a local Docker
stack on 1 November 2026.

## Feature 1: Anonymous Card Posting (Table 2)

| Requirement | Target | Where | Check | Status |
|---|---|---|---|---|
| Card text length | 1 to 280 chars, client and server | `Composer.tsx` (`maxLength`, counter); `cards/serializers.py` | `test_text_length_1_to_280` | Done |
| Image attachment | 0 to 1, JPEG/PNG up to 5 MB, EXIF stripped | `Composer.tsx`; `cards/images.py` | `test_image_exif_is_stripped`, `test_rejects_non_jpeg_png`, `test_rejects_images_over_limit` | Done |
| Steps to publish | 2: write, place | `Composer.tsx` then tap on `CanvasView.tsx` | browser test | Done |
| Identity fields stored | 0 | `cards/models.py` (no identity columns); token hash in separate `RateLimitEvent` | `test_no_identity_stored_on_card`, `test_public_shape_has_no_identity_or_prompt` | Done |
| Posts per session | 5 per hour | `cards/ratelimit.py` | `test_rate_limit_five_per_hour` | Done |
| Submit to visible | 2 s incl. moderation | `cards/views.py` | browser test: card on screen right after tap | Done |

## Feature 2: Shared Spatial Canvas (Table 3)

| Requirement | Target | Where | Check | Status |
|---|---|---|---|---|
| Cards per viewport query | max 200, bbox only | `canvas/spatial.py` | `test_caps_at_200_cards`, `test_returns_only_cards_inside_bbox` | Done |
| Viewport response time | p95 300 ms at 10,000 cards | GiST index, `cards/migrations/0002_spatial_index.py` | `manage.py bench_viewport`: p95 5 ms; via HTTP p95 25 ms | Done |
| Zoom range | 0.25x to 4x, marks below 0.5x | `lib/camera.ts`; `CanvasView.tsx` (`Dot`) | browser test (dots view) | Done |
| Frame rate while panning | 30 fps on a 2022 mid-range Android | DOM transform layer, only visible cards rendered | **not measured on a real phone yet** | Open |
| Minimum viewport | 360 px, mobile first | `globals.css` (`min-width: 360px`), bottom-sheet composer | browser test at 390 px | Done |
| Cards on the canvas | 10,000 | bounded memory in `LightsOut.tsx`, index on server | benchmark at 10,000 | Done |

## Feature 3: Nightly Prompt (Table 4)

| Requirement | Target | Where | Check | Status |
|---|---|---|---|---|
| Active prompts | exactly 1 | `prompts/schedule.py` | `test_exactly_one_prompt_and_no_repeat_for_60_nights` | Done |
| Prompt window | 21:00 to 05:00 reader local time; previous stays visible outside | `schedule.py`, `PromptBanner.tsx` | `test_window_21_to_05`, `test_outside_window_keeps_previous_prompt`, `test_uses_reader_local_time` | Done |
| Prompt bank at launch | 60 | `seed/prompts.json` | `test_seed_loads_200_cards_and_60_prompts` | Done (drafts, team to rewrite) |
| Prompt length | max 60 chars | `prompts/models.py` | seed test | Done |
| Attribution of answers | none | `Card.prompt` kept internal, not in API | `test_answer_is_plain_card_linked_internally` | Done |

## Feature 4: Live Card Delivery (Table 5)

| Requirement | Target | Where | Check | Status |
|---|---|---|---|---|
| Delivery latency | 3 s, by canvas region | `realtime/tiles.py`, `broadcast.py`, `consumers.py` | `test_card_reaches_reader_in_same_region_within_3s`; browser test 121 ms | Done |
| Concurrent connections | 100 | Channels + Redis | `tools/ws_load_test.py`: 100/100 in 0.09 s | Done |
| Reconnect after dropout | 5 s, re-subscribe and refetch | `lib/live.ts` (backoff capped at 3 s, `onResync`) | code review | Done |
| Fallback without WebSocket | 30 s polling, no error shown | `lib/live.ts` | code review; badge shows "updating every 30 s" | Done |

## Feature 5: Moderation and Safety (Table 6)

| Requirement | Target | Where | Check | Status |
|---|---|---|---|---|
| Cards screened automatically | 100%, before publication | `moderation/pipeline.py` called in `cards/views.py` | `test_every_card_is_screened_and_logged` | Done |
| Classifier check | keyword and classifier | `moderation/classifier.py` | keyword heuristic only | **Partial**: trained classifier is a TODO |
| Response to a flagged card | 24 h, team rota | admin review queue, "Waiting" column turns red after 24 h | `docs/moderation-policy.md` | Partial: rota to be confirmed |
| Steps to report | 1 tap, no account | `CardView.tsx` menu; `POST /api/cards/<id>/report/` | `test_one_tap_report_no_account`; browser test | Done |
| Crisis handling | withheld at once, resources shown | `pipeline.screen`, `SupportPanel.tsx` | `test_crisis_card_is_withheld_and_resources_shown`; browser test | Done |
| Retention of removed cards | 30 days then deleted | `purge_removed_cards`, worker service | `test_removed_cards_purged_after_30_days` | Done |
| No poster identity in logs | 0 | `moderation/models.py` | `test_report_stores_no_reporter_identity` | Done |
| Photo screening | (implied by "every card is screened") | | | **Open**: photos rely on reports only |

## Team decision, 1 November 2026: Pinterest-style feed as the default view

The team made a Pinterest-style feed the default way to read cards, with the
shared canvas one tap away. Feature 2 is unchanged and still meets Table 3.
The feed keeps the proposal's principle of no ranking: its order is a random
shuffle per visit, not recency or popularity.

| Item | Where | Check | Status |
|---|---|---|---|
| Masonry columns (2 on phones, up to 5 on wide screens), scrolled top to bottom | `FeedView.tsx` | browser test | Done |
| Shuffled order, stable within a visit, new order per visit | `cards/feed.py` | `test_feed.py` (6 tests) | Done |
| Infinite scroll | `FeedView.tsx` | browser test: 80 to 200 cards | Done |
| Live cards in a "Just now" block | `LightsOut.tsx` | browser test: 0.19 s phone to desktop | Done |
| Feed / Canvas switch, remembered per device | `LightsOut.tsx` | browser test | Done |
| One-step posting from the feed (card placed on the canvas automatically) | `LightsOut.tsx` | browser test | Done |

**Proposal text to update:** Section 3, Feature 2 still describes the canvas as
the only way to read. Add one paragraph on the feed as the default view and why
(familiar pattern for first-time visitors, see the reception-centred finding in
the user research), and note it in the revision history.

## Weekly-update items (Weeks 7 to 10)

| Item | Where | Status |
|---|---|---|
| Repository and PostgreSQL schema for cards | `backend/apps/cards/models.py`, migrations | Done |
| Next.js project and canvas layout | `frontend/` | Done |
| Shared development environment for everyone | `docker-compose.yml`, `README.md` | Done |
| API endpoint to create a card and get all cards | `POST/GET /api/cards/` | Done |
| Card component on the canvas | `CardView.tsx` | Done |
| Front end connected to the API | `lib/api.ts` | Done |
| Real-time updates | Feature 4 | Done |
| Form for writing a card with a character limit | `Composer.tsx` | Done |
| Basic moderation and a posting limit | Feature 5, rate limit | Done |
| Dark late-night theme and mobile layout | `globals.css` | Done |
| Starter cards so the canvas is not empty | `seed/cards.json` (200) | Done (drafts, team to rewrite) |
| Deploy a test version online | | **Open**: runs locally in Docker only |

## Gantt items still ahead (from 2 November)

| Task | Dates | Status |
|---|---|---|
| Seed content and feature freeze | 1 to 8 Nov | Seed drafts in place; team rewrite pending |
| Usability testing and fixes | 8 to 22 Nov | Open |
| Performance and accessibility | 22 to 29 Nov | Server targets met; phone fps and accessibility audit open |
| Deployment and final QA | 29 Nov to 4 Dec | Open |
| Documentation and submission | 4 to 9 Dec | `docs/` started |
