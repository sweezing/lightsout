"use client";

//Pinterest-style feed: cards of different heights packed into columns,
//scrolled top to bottom, loaded page by page as the reader nears the end.
//
//order is a per-visit shuffle from the API, so nothing is "at the top"
//because it is popular or new. cards that arrive live while reading are
//shown in a small "just now" block above the feed instead of being pushed
//into the columns, so the layout never jumps under the reader's thumb.

import { ReactNode, useEffect, useMemo, useRef, useState } from "react";

import type { Card, ReportReason } from "@/lib/types";

import CardView from "./CardView";

type Props = {
  items: Card[];
  justNow: Card[];
  fresh: Set<string>;
  loading: boolean;
  hasMore: boolean;
  onLoadMore: () => void;
  onReport: (id: string, reason: ReportReason) => void;
  header?: ReactNode;
};

const GAP = 12;
const MOBILE_GAP = 10;

function columnCount(width: number) {
  if (width < 640) return 2;
  if (width < 1000) return 3;
  if (width < 1400) return 4;
  return 5;
}

/** rough rendered height of a card, good enough for shortest-column packing. */
function estimateHeight(card: Card, colWidth: number) {
  const big = card.text.length <= 70;
  const charW = big ? 10.6 : 8.4;
  const lineH = big ? 30 : 23;
  const perLine = Math.max(8, Math.floor((colWidth - 32) / charW));
  const lines = card.text
    .split("\n")
    .reduce((n, part) => n + Math.max(1, Math.ceil(part.length / perLine)), 0);
  const image = card.image ? colWidth * 0.75 + 10 : 0;
  return 58 + lines * lineH + image;
}

function pack(cards: Card[], cols: number, colWidth: number): Card[][] {
  const columns: Card[][] = Array.from({ length: cols }, () => []);
  const heights = new Array(cols).fill(0);
  for (const c of cards) {
    let target = 0;
    for (let i = 1; i < cols; i++) if (heights[i] < heights[target]) target = i;
    columns[target].push(c);
    heights[target] += estimateHeight(c, colWidth) + GAP;
  }
  return columns;
}

function Masonry({
  cards,
  cols,
  width,
  fresh,
  onReport,
}: {
  cards: Card[];
  cols: number;
  width: number;
  fresh: Set<string>;
  onReport: Props["onReport"];
}) {
  const gap = width < 640 ? MOBILE_GAP : GAP;
  const colWidth = (width - gap * (cols - 1)) / cols;
  const columns = useMemo(() => pack(cards, cols, colWidth), [cards, cols, colWidth]);
  return (
    <div className="masonry" style={{ gap }}>
      {columns.map((col, i) => (
        <div className="masonry-col" key={i} style={{ gap }}>
          {col.map((c) => (
            <CardView key={c.id} card={c} fresh={fresh.has(c.id)} onReport={onReport} variant="feed" />
          ))}
        </div>
      ))}
    </div>
  );
}

export default function FeedView(p: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const innerRef = useRef<HTMLDivElement>(null);
  const sentinelRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(0);
  const { onLoadMore, hasMore, loading } = p;

  useEffect(() => {
    const el = innerRef.current!;
    const ro = new ResizeObserver(([e]) => setWidth(e.contentRect.width));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  //infinite scroll: load the next page well before the reader hits the end.
  useEffect(() => {
    const el = sentinelRef.current;
    if (!el) return;
    const io = new IntersectionObserver(
      ([e]) => {
        if (e.isIntersecting && hasMore && !loading) onLoadMore();
      },
      { root: scrollRef.current, rootMargin: "900px 0px" },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [onLoadMore, hasMore, loading]);

  const cols = columnCount(width);

  return (
    <div className="feed" ref={scrollRef}>
      <div className="feed-inner" ref={innerRef}>
        {p.header}

        {width > 0 && p.justNow.length > 0 && (
          <section className="just-now" aria-label="Posted just now">
            <h2 className="feed-label">
              <span className="live-dot" aria-hidden /> Just now
            </h2>
            <Masonry cards={p.justNow} cols={cols} width={width} fresh={p.fresh} onReport={p.onReport} />
          </section>
        )}

        {width > 0 && (
          <Masonry cards={p.items} cols={cols} width={width} fresh={p.fresh} onReport={p.onReport} />
        )}

        <div ref={sentinelRef} className="feed-end" role="status">
          {loading
            ? "Turning on more lights…"
            : !hasMore && p.items.length > 0
              ? "That's everyone awake for now. Come back later."
              : !hasMore && p.items.length === 0
                ? "Nothing here yet. You could be the first light tonight."
                : ""}
        </div>
      </div>
    </div>
  );
}
