"use client";

//page orchestrator. two ways to read the same cards:
//
//feed    (default) Pinterest-style columns, scrolled top to bottom,
//shuffled per visit, infinite scroll.
//canvas  feature 2: the shared spatial canvas with pan and zoom.
//
//both share the live connection, the composer, reports and support panel.

import { useCallback, useEffect, useRef, useState } from "react";

import { fetchFeed, fetchLatest, fetchViewport, postCard, reportCard } from "@/lib/api";
import { Camera, Size, WORLD_HALF, clampCamera, contains, covers, visibleBBox } from "@/lib/camera";
import { LiveClient } from "@/lib/live";
import type { BBox, Card, LiveStatus, PostResult, ReportReason, SupportResource } from "@/lib/types";

import CanvasView from "./CanvasView";
import Composer, { Draft } from "./Composer";
import FeedView from "./FeedView";
import PromptBanner from "./PromptBanner";
import SupportPanel from "./SupportPanel";

type View = "feed" | "canvas";

const HOME: Camera = { x: 0, y: 0, zoom: 1 };
const FETCH_MARGIN = 1.6; //canvas: load a bit beyond the screen so panning feels instant
const KEEP_MARGIN = 4; //canvas: forget cards far outside the view
const MAX_CARDS_IN_MEMORY = 2000;
const WHOLE_WORLD: BBox = { min_x: -WORLD_HALF, min_y: -WORLD_HALF, max_x: WORLD_HALF, max_y: WORLD_HALF };
const FEED_POST_RADIUS = 2600; //feed posts land somewhere in the busy middle of the canvas
const VIEW_KEY = "lightsout.view";

type Support = { message: string | null; resources: SupportResource[] | null };

function randomSeed() {
  return Math.random().toString(36).slice(2, 12);
}

function randomSpot() {
  const r = FEED_POST_RADIUS * Math.sqrt(Math.random());
  const a = Math.random() * Math.PI * 2;
  return { x: r * Math.cos(a), y: r * Math.sin(a) };
}

export default function LightsOut() {
  const [view, setView] = useState<View>("feed");

  //---- canvas state
  const [camera, setCamera] = useState<Camera>(HOME);
  const [size, setSize] = useState<Size>({ w: 0, h: 0 });
  const [cards, setCards] = useState<Map<string, Card>>(() => new Map());
  const [canvasLoaded, setCanvasLoaded] = useState(false);

  //---- feed state
  const [seed] = useState(randomSeed);
  const [feedItems, setFeedItems] = useState<Card[]>([]);
  const [justNow, setJustNow] = useState<Card[]>([]);
  const [feedOffset, setFeedOffset] = useState<number | null>(0);
  const [feedLoading, setFeedLoading] = useState(false);
  const openedAt = useRef(Date.now());

  //---- shared state
  const [fresh, setFresh] = useState<Set<string>>(() => new Set());
  const [live, setLive] = useState<LiveStatus>("connecting");
  const [composerOpen, setComposerOpen] = useState(false);
  const [draft, setDraft] = useState<Draft>({ text: "", image: null });
  const [composerError, setComposerError] = useState<string | null>(null);
  const [placeholder, setPlaceholder] = useState<string | null>(null);
  const [placing, setPlacing] = useState(false);
  const [posting, setPosting] = useState(false);
  const [support, setSupport] = useState<Support | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const viewRef = useRef(view);
  const cameraRef = useRef(camera);
  const sizeRef = useRef(size);
  viewRef.current = view;
  cameraRef.current = camera;
  sizeRef.current = size;
  const fetchedRef = useRef<BBox | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const liveRef = useRef<LiveClient | null>(null);
  const seenRef = useRef(new Set<string>()); //every card id the feed has shown

  //remember the reader's view choice on this device.
  useEffect(() => {
    try {
      const saved = window.localStorage.getItem(VIEW_KEY);
      if (saved === "canvas" || saved === "feed") setView(saved);
    } catch {
      /*storage blocked: default view */
    }
  }, []);
  const switchView = useCallback((v: View) => {
    setView(v);
    setPlacing(false);
    try {
      window.localStorage.setItem(VIEW_KEY, v);
    } catch {
      /*ignore */
    }
  }, []);

  //------------------------------------------------------------ helpers
  const markFresh = useCallback((ids: string[]) => {
    setFresh((prev) => new Set([...prev, ...ids]));
    setTimeout(() => {
      setFresh((prev) => {
        const next = new Set(prev);
        ids.forEach((id) => next.delete(id));
        return next;
      });
    }, 4000);
  }, []);

  const addToCanvas = useCallback((incoming: Card[]) => {
    if (!incoming.length) return;
    setCards((prev) => {
      const next = new Map(prev);
      for (const c of incoming) next.set(c.id, c);
      return next;
    });
  }, []);

  /** a card that appeared while the page is open: top of the feed + canvas. */
  const arrive = useCallback(
    (incoming: Card[]) => {
      const brandNew = incoming.filter((c) => !seenRef.current.has(c.id));
      if (!brandNew.length) return;
      brandNew.forEach((c) => seenRef.current.add(c.id));
      setJustNow((prev) => [...brandNew, ...prev].slice(0, 60));
      addToCanvas(brandNew);
      markFresh(brandNew.map((c) => c.id));
    },
    [addToCanvas, markFresh],
  );

  const removeEverywhere = useCallback((id: string) => {
    setCards((prev) => {
      if (!prev.has(id)) return prev;
      const next = new Map(prev);
      next.delete(id);
      return next;
    });
    setFeedItems((prev) => prev.filter((c) => c.id !== id));
    setJustNow((prev) => prev.filter((c) => c.id !== id));
  }, []);

  //------------------------------------------------------------ feed loading
  const loadMoreFeed = useCallback(async () => {
    if (feedLoading || feedOffset === null) return;
    setFeedLoading(true);
    try {
      const page = await fetchFeed(seed, feedOffset);
      const unseen = page.cards.filter((c) => !seenRef.current.has(c.id));
      unseen.forEach((c) => seenRef.current.add(c.id));
      setFeedItems((prev) => [...prev, ...unseen]);
      setFeedOffset(page.next_offset);
    } catch (e) {
      console.warn(e);
    } finally {
      setFeedLoading(false);
    }
  }, [feedLoading, feedOffset, seed]);

  useEffect(() => {
    if (view === "feed" && feedItems.length === 0 && feedOffset === 0) loadMoreFeed();
  }, [view, feedItems.length, feedOffset, loadMoreFeed]);

  //------------------------------------------------------------ canvas loading
  const pruneCanvas = useCallback(() => {
    const keep = visibleBBox(cameraRef.current, sizeRef.current, KEEP_MARGIN);
    setCards((prev) => {
      let next: Map<string, Card> | null = null;
      for (const [id, c] of prev) {
        if (!contains(keep, c.x, c.y)) (next ??= new Map(prev)).delete(id);
      }
      const out = next ?? prev;
      if (out.size <= MAX_CARDS_IN_MEMORY) return out;
      return new Map([...out].slice(out.size - MAX_CARDS_IN_MEMORY));
    });
  }, []);

  const loadCanvas = useCallback(
    async (force = false) => {
      const cam = cameraRef.current;
      const s = sizeRef.current;
      if (!s.w) return;
      const want = visibleBBox(cam, s, 1.05);
      if (!force && fetchedRef.current && covers(fetchedRef.current, want)) return;
      const box = visibleBBox(cam, s, FETCH_MARGIN);
      abortRef.current?.abort();
      const ctrl = new AbortController();
      abortRef.current = ctrl;
      try {
        const got = await fetchViewport(box, ctrl.signal);
        fetchedRef.current = box;
        addToCanvas(got);
        pruneCanvas();
      } catch (e) {
        if ((e as Error).name !== "AbortError") console.warn(e);
      } finally {
        setCanvasLoaded(true);
      }
    },
    [addToCanvas, pruneCanvas],
  );

  //coming back to the canvas: forget what was loaded so it refetches.
  useEffect(() => {
    if (view === "canvas") fetchedRef.current = null;
  }, [view]);

  //phones see a narrow slice of the canvas; start a little zoomed out there.
  const sizedOnce = useRef(false);
  useEffect(() => {
    if (!size.w || sizedOnce.current) return;
    sizedOnce.current = true;
    if (size.w < 640) setCamera((c) => clampCamera({ ...c, zoom: 0.75 }));
  }, [size]);

  //debounced reaction to camera moves (canvas) or view switches (feed):
  //fetch what is visible and tell the live socket which regions we watch.
  useEffect(() => {
    if (view === "feed") {
      liveRef.current?.setViewport(WHOLE_WORLD); //the feed wants every new card
      return;
    }
    if (!size.w) return;
    const t = setTimeout(() => {
      loadCanvas();
      liveRef.current?.setViewport(visibleBBox(camera, size, FETCH_MARGIN));
    }, 180);
    return () => clearTimeout(t);
  }, [view, camera, size, loadCanvas]);

  //after a reconnect or on each 30 s poll: catch up on what was missed.
  const resync = useCallback(async () => {
    if (viewRef.current === "canvas") {
      loadCanvas(true);
      return;
    }
    try {
      const latest = await fetchLatest();
      arrive(latest.filter((c) => new Date(c.created_at).getTime() > openedAt.current));
    } catch {
      /*next poll will try again */
    }
  }, [loadCanvas, arrive]);
  const resyncRef = useRef(resync);
  resyncRef.current = resync;

  //one live connection for the lifetime of the page.
  useEffect(() => {
    const client = new LiveClient({
      onCard: (c) => arrive([c]),
      onHidden: removeEverywhere,
      onResync: () => resyncRef.current(),
      onStatus: setLive,
    });
    liveRef.current = client;
    client.start();
    if (viewRef.current === "feed") client.setViewport(WHOLE_WORLD);
    return () => client.stop();
  }, [arrive, removeEverywhere]);

  //------------------------------------------------------------ write flow
  const openComposer = useCallback((hint: string | null = null) => {
    setPlaceholder(hint);
    setComposerError(null);
    setComposerOpen(true);
  }, []);

  const handleResult = useCallback(
    (result: PostResult) => {
      switch (result.status) {
        case "published":
          arrive([result.card]);
          setDraft({ text: "", image: null });
          setComposerOpen(false);
          setToast("Your light is on.");
          if (viewRef.current === "feed") {
            document.querySelector(".feed")?.scrollTo({ top: 0, behavior: "smooth" });
          }
          break;
        case "withheld":
          setDraft({ text: "", image: null });
          setComposerOpen(false);
          setSupport({ message: result.detail, resources: result.resources });
          break;
        default:
          setComposerError(result.detail);
          setComposerOpen(true);
      }
    },
    [arrive],
  );

  const post = useCallback(
    async (x: number, y: number) => {
      if (posting) return;
      setPosting(true);
      const result = await postCard({ text: draft.text, image: draft.image, x, y });
      setPosting(false);
      setPlacing(false);
      handleResult(result);
    },
    [posting, draft, handleResult],
  );

  /** composer's main button. feed: post now. canvas: go on to placing. */
  const submit = useCallback(() => {
    if (viewRef.current === "feed") {
      const spot = randomSpot();
      post(spot.x, spot.y);
    } else {
      setComposerOpen(false);
      setPlacing(true);
    }
  }, [post]);

  const cancelPlacing = useCallback(() => {
    setPlacing(false);
    setComposerOpen(true);
  }, []);

  const report = useCallback(
    async (id: string, reason: ReportReason) => {
      const ok = await reportCard(id, reason);
      if (ok) {
        removeEverywhere(id); //hide it for this reader straight away
        setToast(
          reason === "worried"
            ? "Thank you. A person on the team will look at it soon."
            : "Thanks. It's hidden for you and a person will review it.",
        );
      } else {
        setToast("Couldn't send the report. Try again in a moment.");
      }
    },
    [removeEverywhere],
  );

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 3500);
    return () => clearTimeout(t);
  }, [toast]);

  //------------------------------------------------------------ keyboard
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement | null;
      if (el && (el.tagName === "TEXTAREA" || el.tagName === "INPUT" || el.isContentEditable)) return;
      if (composerOpen || support) return;
      if ((e.key === "n" || e.key === "N") && !placing) {
        openComposer();
        e.preventDefault();
        return;
      }
      if (viewRef.current !== "canvas") return;
      const step = 120 / cameraRef.current.zoom;
      const move = (dx: number, dy: number, f = 1) =>
        setCamera((c) => clampCamera({ x: c.x + dx, y: c.y + dy, zoom: c.zoom * f }));
      switch (e.key) {
        case "ArrowLeft": move(-step, 0); break;
        case "ArrowRight": move(step, 0); break;
        case "ArrowUp": move(0, -step); break;
        case "ArrowDown": move(0, step); break;
        case "+": case "=": move(0, 0, 1.25); break;
        case "-": case "_": move(0, 0, 0.8); break;
        case "0": setCamera(HOME); break;
        case "Escape": if (placing) cancelPlacing(); break;
        default: return;
      }
      e.preventDefault();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [composerOpen, support, placing, openComposer, cancelPlacing]);

  //------------------------------------------------------------ render
  const visible = visibleBBox(camera, size, 1.2);
  const shown = view === "canvas" ? [...cards.values()].filter((c) => contains(visible, c.x, c.y)) : [];

  return (
    <main className={`app app--${view}`}>
      <header className="topbar">
        <div className="brand">
          <span className="brand-dot" aria-hidden />
          Lights Out
        </div>
        <LiveBadge status={live} />
        <div className="view-switch" role="tablist" aria-label="How to read the cards">
          <button role="tab" aria-selected={view === "feed"} onClick={() => switchView("feed")}>
            Feed
          </button>
          <button role="tab" aria-selected={view === "canvas"} onClick={() => switchView("canvas")}>
            Canvas
          </button>
        </div>
        <button
          className="link-button help-link"
          aria-label="Need to talk to someone?"
          onClick={() => setSupport({ message: null, resources: null })}
        >
          <span className="label-long">Need to talk to someone?</span>
          <span className="label-short">Support</span>
        </button>
      </header>

      {view === "feed" ? (
        <FeedView
          items={feedItems}
          justNow={justNow}
          fresh={fresh}
          loading={feedLoading}
          hasMore={feedOffset !== null}
          onLoadMore={loadMoreFeed}
          onReport={report}
          header={<PromptBanner inline onAnswer={(text) => openComposer(text)} />}
        />
      ) : (
        <>
          <PromptBanner onAnswer={(text) => openComposer(text)} />
          <CanvasView
            camera={camera}
            onCamera={setCamera}
            onSize={setSize}
            cards={shown}
            fresh={fresh}
            placing={placing}
            posting={posting}
            draftText={draft.text}
            onPlace={post}
            onReport={report}
          />
          {canvasLoaded && shown.length === 0 && !placing && (
            <p className="empty" role="status">
              Nothing here yet. You could be the first light in this corner.
            </p>
          )}
        </>
      )}

      {placing ? (
        <div className="placebar" role="status">
          <span>{posting ? "Posting…" : "Tap where your card should live."}</span>
          <div className="placebar-actions">
            <button className="button ghost" disabled={posting} onClick={() => post(camera.x, camera.y)}>
              Put it in the middle
            </button>
            <button className="button ghost" disabled={posting} onClick={cancelPlacing}>
              Back
            </button>
          </div>
        </div>
      ) : (
        <nav className="bottombar" aria-label="Controls">
          {view === "canvas" ? (
            <div className="zoom">
              <button aria-label="Zoom out" onClick={() => setCamera((c) => clampCamera({ ...c, zoom: c.zoom * 0.8 }))}>−</button>
              <button aria-label="Back to the centre" onClick={() => setCamera(HOME)}>◎</button>
              <button aria-label="Zoom in" onClick={() => setCamera((c) => clampCamera({ ...c, zoom: c.zoom * 1.25 }))}>+</button>
            </div>
          ) : (
            <span />
          )}
          <button className="button primary write" onClick={() => openComposer()}>
            Write a card
          </button>
        </nav>
      )}

      {composerOpen && (
        <Composer
          draft={draft}
          onChange={setDraft}
          placeholder={placeholder}
          error={composerError}
          submitLabel={view === "feed" ? "Post it" : "Place it on the canvas →"}
          busy={posting}
          onNext={submit}
          onClose={() => setComposerOpen(false)}
        />
      )}

      {support && (
        <SupportPanel message={support.message} resources={support.resources} onClose={() => setSupport(null)} />
      )}

      {toast && <div className="toast" role="status">{toast}</div>}
    </main>
  );
}

function LiveBadge({ status }: { status: LiveStatus }) {
  const label = status === "live" ? "live" : status === "polling" ? "updating every 30 s" : "connecting…";
  return (
    <span className={`live live-${status}`} title="New cards appear without a refresh">
      <span className="live-dot" aria-hidden />
      {label}
    </span>
  );
}
