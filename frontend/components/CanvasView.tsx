"use client";

//feature 2 - the shared spatial canvas.
//one continuous plane with no ordering: nothing is at the top, so nothing is
//winning. pan with drag / one finger, zoom with pinch, ctrl+wheel or buttons.
//below 0.5x zoom cards turn into small lights, which keeps the sense of scale
//and stays fast on a phone.

import { memo, useEffect, useRef } from "react";

import { Camera, DOTS_BELOW, Size, clampCamera, screenToWorld, zoomAt } from "@/lib/camera";
import type { Card, ReportReason } from "@/lib/types";

import CardView from "./CardView";

type Props = {
  camera: Camera;
  onCamera: (c: Camera | ((c: Camera) => Camera)) => void;
  onSize: (s: Size) => void;
  cards: Card[];
  fresh: Set<string>;
  placing: boolean;
  posting: boolean;
  draftText: string;
  onPlace: (x: number, y: number) => void;
  onReport: (id: string, reason: ReportReason) => void;
};

type Pt = { x: number; y: number };
const TAP_SLOP = 6;

export default function CanvasView(p: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const sizeRef = useRef<Size>({ w: 0, h: 0 });
  const pointers = useRef(new Map<number, Pt>());
  const gesture = useRef<{ start: Pt; moved: boolean; pinchDist: number | null }>({
    start: { x: 0, y: 0 },
    moved: false,
    pinchDist: null,
  });
  const ghostRef = useRef<HTMLDivElement>(null);
  const { onCamera, onSize } = p;

  //track the surface size.
  useEffect(() => {
    const el = ref.current!;
    const ro = new ResizeObserver(([entry]) => {
      const s = { w: entry.contentRect.width, h: entry.contentRect.height };
      sizeRef.current = s;
      onSize(s);
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, [onSize]);

  //wheel: ctrl/cmd (and trackpad pinch) zooms around the cursor, plain wheel pans.
  useEffect(() => {
    const el = ref.current!;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const r = el.getBoundingClientRect();
      const sx = e.clientX - r.left;
      const sy = e.clientY - r.top;
      if (e.ctrlKey || e.metaKey) {
        const factor = Math.exp(-e.deltaY * 0.01);
        onCamera((c) => zoomAt(c, sizeRef.current, sx, sy, factor));
      } else {
        onCamera((c) => clampCamera({ ...c, x: c.x + e.deltaX / c.zoom, y: c.y + e.deltaY / c.zoom }));
      }
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, [onCamera]);

  const local = (e: React.PointerEvent): Pt => {
    const r = ref.current!.getBoundingClientRect();
    return { x: e.clientX - r.left, y: e.clientY - r.top };
  };

  const onPointerDown = (e: React.PointerEvent) => {
    if ((e.target as HTMLElement).closest("button, a, [data-no-pan]")) return;
    ref.current!.setPointerCapture(e.pointerId);
    const pt = local(e);
    pointers.current.set(e.pointerId, pt);
    if (pointers.current.size === 1) {
      gesture.current = { start: pt, moved: false, pinchDist: null };
    } else if (pointers.current.size === 2) {
      const [a, b] = [...pointers.current.values()];
      gesture.current.pinchDist = Math.hypot(a.x - b.x, a.y - b.y);
      gesture.current.moved = true;
    }
  };

  const onPointerMove = (e: React.PointerEvent) => {
    const pt = local(e);
    if (p.placing && ghostRef.current) {
      ghostRef.current.style.transform = `translate(${pt.x}px, ${pt.y}px)`;
    }
    const prev = pointers.current.get(e.pointerId);
    if (!prev) return;
    pointers.current.set(e.pointerId, pt);
    const g = gesture.current;

    if (pointers.current.size === 1) {
      if (Math.hypot(pt.x - g.start.x, pt.y - g.start.y) > TAP_SLOP) g.moved = true;
      const dx = pt.x - prev.x;
      const dy = pt.y - prev.y;
      onCamera((c) => clampCamera({ ...c, x: c.x - dx / c.zoom, y: c.y - dy / c.zoom }));
    } else if (pointers.current.size === 2) {
      const [a, b] = [...pointers.current.values()];
      const dist = Math.hypot(a.x - b.x, a.y - b.y);
      const mid = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
      if (g.pinchDist) {
        const factor = dist / g.pinchDist;
        onCamera((c) => zoomAt(c, sizeRef.current, mid.x, mid.y, factor));
      }
      g.pinchDist = dist;
    }
  };

  const onPointerUp = (e: React.PointerEvent) => {
    const had = pointers.current.delete(e.pointerId);
    if (!had) return;
    if (pointers.current.size < 2) gesture.current.pinchDist = null;
    if (pointers.current.size === 0 && p.placing && !p.posting && !gesture.current.moved) {
      const pt = local(e);
      const w = screenToWorld(p.camera, sizeRef.current, pt.x, pt.y);
      p.onPlace(w.x, w.y);
    }
  };

  const { camera, cards } = p;
  const s = sizeRef.current;
  const dots = camera.zoom < DOTS_BELOW;
  const layer = {
    transform: `translate3d(${s.w / 2 - camera.x * camera.zoom}px, ${s.h / 2 - camera.y * camera.zoom}px, 0) scale(${camera.zoom})`,
  };

  return (
    <div
      ref={ref}
      className={`canvas${p.placing ? " placing" : ""}`}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerUp}
      role="application"
      aria-label="Shared canvas of anonymous cards. Drag to move, pinch or use the plus and minus buttons to zoom."
    >
      <div className="sky" aria-hidden />
      <div className="layer" style={layer}>
        {dots
          ? cards.map((c) => <Dot key={c.id} card={c} fresh={p.fresh.has(c.id)} />)
          : cards.map((c) => (
              <CardView key={c.id} card={c} fresh={p.fresh.has(c.id)} onReport={p.onReport} />
            ))}
      </div>
      {p.placing && (
        <div ref={ghostRef} className="place-ghost" aria-hidden>
          <div className="place-ghost-card">{p.draftText}</div>
        </div>
      )}
    </div>
  );
}

const Dot = memo(function Dot({ card, fresh }: { card: Card; fresh: boolean }) {
  return (
    <div
      className={`dot${fresh ? " fresh" : ""}`}
      style={{ left: card.x, top: card.y }}
      title={card.text}
    />
  );
});
