//live card delivery client (feature 4, table 5).
//
//- WebSocket to /ws/canvas/, subscribed to the regions in view
//- reconnects with backoff capped at 3 s, so recovery stays under 5 s
//- after a reconnect: re-subscribe and ask the page to refetch the viewport
//- if the socket stays down, fall back to polling the viewport every 30 s,
//silently (no error is shown to the reader)

import type { BBox, Card, LiveStatus } from "./types";

const BACKOFF_MS = [300, 1000, 2000, 3000];
const POLL_MS = 30_000;
const FALLBACK_AFTER_MS = 8_000;
const PING_MS = 25_000;

type Handlers = {
  onCard: (c: Card) => void;
  onHidden: (id: string) => void;
  onResync: () => void; //refetch the viewport (after reconnect, and on each poll)
  onStatus: (s: LiveStatus) => void;
};

export class LiveClient {
  private ws: WebSocket | null = null;
  private attempt = 0;
  private viewport: BBox | null = null;
  private retryTimer: ReturnType<typeof setTimeout> | null = null;
  private pollTimer: ReturnType<typeof setInterval> | null = null;
  private fallbackTimer: ReturnType<typeof setTimeout> | null = null;
  private pingTimer: ReturnType<typeof setInterval> | null = null;
  private everConnected = false;
  private closed = false;

  constructor(private h: Handlers) {}

  start() {
    this.closed = false;
    if (typeof WebSocket === "undefined") {
      this.startPolling();
      return;
    }
    this.armFallback();
    this.connect();
  }

  stop() {
    this.closed = true;
    this.clearTimers();
    this.ws?.close();
    this.ws = null;
  }

  setViewport(b: BBox) {
    this.viewport = b;
    this.send({ type: "viewport", ...b });
  }

  private url() {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    return `${proto}://${location.host}/ws/canvas/`;
  }

  private connect() {
    this.h.onStatus(this.pollTimer ? "polling" : "connecting");
    let ws: WebSocket;
    try {
      ws = new WebSocket(this.url());
    } catch {
      this.scheduleRetry();
      return;
    }
    this.ws = ws;

    ws.onopen = () => {
      const isReconnect = this.everConnected;
      this.everConnected = true;
      this.attempt = 0;
      this.stopPolling();
      if (this.fallbackTimer) clearTimeout(this.fallbackTimer);
      this.h.onStatus("live");
      if (this.viewport) this.send({ type: "viewport", ...this.viewport });
      if (isReconnect) this.h.onResync(); //pick up anything missed while offline
      this.pingTimer = setInterval(() => this.send({ type: "ping" }), PING_MS);
    };

    ws.onmessage = (ev) => {
      let msg: { type?: string; card?: Card; id?: string };
      try {
        msg = JSON.parse(ev.data);
      } catch {
        return;
      }
      if (msg.type === "card.created" && msg.card) this.h.onCard(msg.card);
      else if (msg.type === "card.hidden" && msg.id) this.h.onHidden(msg.id);
    };

    ws.onclose = () => {
      if (this.pingTimer) clearInterval(this.pingTimer);
      this.ws = null;
      if (this.closed) return;
      this.armFallback();
      this.scheduleRetry();
    };

    ws.onerror = () => ws.close();
  }

  private scheduleRetry() {
    if (this.closed) return;
    const delay = BACKOFF_MS[Math.min(this.attempt, BACKOFF_MS.length - 1)];
    this.attempt += 1;
    this.retryTimer = setTimeout(() => this.connect(), delay);
  }

  private armFallback() {
    if (this.fallbackTimer || this.pollTimer) return;
    this.fallbackTimer = setTimeout(() => {
      this.fallbackTimer = null;
      if (!this.ws || this.ws.readyState !== WebSocket.OPEN) this.startPolling();
    }, FALLBACK_AFTER_MS);
  }

  private startPolling() {
    if (this.pollTimer) return;
    this.h.onStatus("polling");
    this.pollTimer = setInterval(() => this.h.onResync(), POLL_MS);
  }

  private stopPolling() {
    if (this.pollTimer) clearInterval(this.pollTimer);
    this.pollTimer = null;
  }

  private send(obj: unknown) {
    if (this.ws?.readyState === WebSocket.OPEN) this.ws.send(JSON.stringify(obj));
  }

  private clearTimers() {
    for (const t of [this.retryTimer, this.fallbackTimer]) if (t) clearTimeout(t);
    for (const t of [this.pollTimer, this.pingTimer]) if (t) clearInterval(t);
    this.retryTimer = this.fallbackTimer = this.pollTimer = this.pingTimer = null;
  }
}
