//canvas camera math (feature 2).
//world units are the same units the API stores in card.x / card.y.
//the camera's (x, y) is the world point at the centre of the screen.

import type { BBox } from "./types";

export const ZOOM_MIN = 0.25;
export const ZOOM_MAX = 4;
export const DOTS_BELOW = 0.5; //below this zoom cards render as unreadable marks
export const WORLD_HALF = 50_000;

export type Camera = { x: number; y: number; zoom: number };
export type Size = { w: number; h: number };

export const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

export function clampCamera(c: Camera): Camera {
  return {
    x: clamp(c.x, -WORLD_HALF, WORLD_HALF),
    y: clamp(c.y, -WORLD_HALF, WORLD_HALF),
    zoom: clamp(c.zoom, ZOOM_MIN, ZOOM_MAX),
  };
}

export function screenToWorld(c: Camera, s: Size, sx: number, sy: number) {
  return { x: c.x + (sx - s.w / 2) / c.zoom, y: c.y + (sy - s.h / 2) / c.zoom };
}

/** zoom by `factor` keeping the world point under (sx, sy) fixed on screen. */
export function zoomAt(c: Camera, s: Size, sx: number, sy: number, factor: number): Camera {
  const zoom = clamp(c.zoom * factor, ZOOM_MIN, ZOOM_MAX);
  const before = screenToWorld(c, s, sx, sy);
  const after = screenToWorld({ ...c, zoom }, s, sx, sy);
  return clampCamera({ x: c.x + before.x - after.x, y: c.y + before.y - after.y, zoom });
}

/** visible world rectangle, optionally grown by `margin` (1 = exact). */
export function visibleBBox(c: Camera, s: Size, margin = 1): BBox {
  const hw = (s.w / 2 / c.zoom) * margin;
  const hh = (s.h / 2 / c.zoom) * margin;
  return { min_x: c.x - hw, min_y: c.y - hh, max_x: c.x + hw, max_y: c.y + hh };
}

export function contains(b: BBox, x: number, y: number) {
  return x >= b.min_x && x <= b.max_x && y >= b.min_y && y <= b.max_y;
}

export function covers(outer: BBox, inner: BBox) {
  return (
    outer.min_x <= inner.min_x && outer.min_y <= inner.min_y &&
    outer.max_x >= inner.max_x && outer.max_y >= inner.max_y
  );
}
