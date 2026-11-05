import type { BBox, Card, PostResult, Prompt, ReportReason, SupportResource } from "./types";
import { sessionToken } from "./session";

//same origin: nginx routes /api/ to Django.
const API = "/api";

export function tzOffsetMinutes(): number {
  //getTimezoneOffset() is minutes WEST of UTC; the API wants minutes east.
  return -new Date().getTimezoneOffset();
}

export async function fetchViewport(b: BBox, signal?: AbortSignal): Promise<Card[]> {
  const q = new URLSearchParams({
    min_x: String(Math.round(b.min_x)),
    min_y: String(Math.round(b.min_y)),
    max_x: String(Math.round(b.max_x)),
    max_y: String(Math.round(b.max_y)),
  });
  const r = await fetch(`${API}/canvas/viewport/?${q}`, { signal, cache: "no-store" });
  if (!r.ok) throw new Error(`viewport ${r.status}`);
  return (await r.json()).cards as Card[];
}

/** Pinterest-style feed: a stable shuffle per `seed`, paged for infinite scroll. */
export async function fetchFeed(
  seed: string,
  offset: number,
  limit = 40,
): Promise<{ cards: Card[]; next_offset: number | null }> {
  const q = new URLSearchParams({ seed, offset: String(offset), limit: String(limit) });
  const r = await fetch(`${API}/cards/feed/?${q}`, { cache: "no-store" });
  if (!r.ok) throw new Error(`feed ${r.status}`);
  return r.json();
}

/** newest published cards; used to catch up after the live socket was down. */
export async function fetchLatest(): Promise<Card[]> {
  const r = await fetch(`${API}/cards/`, { cache: "no-store" });
  if (!r.ok) throw new Error(`latest ${r.status}`);
  return r.json();
}

export async function fetchPrompt(): Promise<Prompt> {
  const r = await fetch(`${API}/prompt/current/?tz_offset=${tzOffsetMinutes()}`, { cache: "no-store" });
  if (!r.ok) throw new Error(`prompt ${r.status}`);
  return r.json();
}

export async function fetchResources(): Promise<SupportResource[]> {
  const r = await fetch(`${API}/moderation/resources/`);
  if (!r.ok) return [];
  return (await r.json()).resources;
}

export async function postCard(input: { text: string; x: number; y: number; image?: File | null }): Promise<PostResult> {
  const form = new FormData();
  form.set("text", input.text);
  form.set("x", String(Math.round(input.x)));
  form.set("y", String(Math.round(input.y)));
  form.set("tz_offset", String(tzOffsetMinutes()));
  if (input.image) form.set("image", input.image);

  let r: Response;
  try {
    r = await fetch(`${API}/cards/`, {
      method: "POST",
      body: form,
      headers: { "X-Session-Token": sessionToken() },
    });
  } catch {
    return { status: "error", detail: "Couldn't reach the canvas. Check your connection and try again." };
  }

  const body = await r.json().catch(() => ({}));
  if (r.status === 201) return { status: "published", card: body.card };
  if (r.status === 202) return { status: "withheld", detail: body.detail, resources: body.resources ?? [] };
  if (r.status === 422) return { status: "rejected", detail: body.detail };
  if (r.status === 429) return { status: "rate_limited", detail: body.detail };
  const first = body && typeof body === "object" ? Object.values(body)[0] : null;
  const detail = Array.isArray(first) ? String(first[0]) : typeof first === "string" ? first : "Something went wrong.";
  return { status: "error", detail };
}

export async function reportCard(id: string, reason: ReportReason): Promise<boolean> {
  const r = await fetch(`${API}/cards/${id}/report/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reason }),
  });
  return r.ok;
}
