"use client";

//a single card on the canvas. no author, no likes, no counts: just the
//thought, and a quiet way to report it (feature 5: one tap, no account).

import { memo, useState } from "react";

import type { Card, ReportReason } from "@/lib/types";

import { useCardMenu } from "./CardMenuContext";

const REASONS: { value: ReportReason; label: string }[] = [
  { value: "harmful", label: "Harmful or abusive" },
  { value: "personal_info", label: "Shares personal information" },
  { value: "spam", label: "Spam" },
  { value: "worried", label: "I'm worried about this person" },
  { value: "other", label: "Something else" },
];

type Props = {
  card: Card;
  fresh: boolean;
  onReport: (id: string, reason: ReportReason) => void;
  /** "canvas": positioned on the shared canvas. "feed": a pin in the Pinterest-style feed. */
  variant?: "canvas" | "feed";
};

const BIG_TEXT_MAX = 70; //short thoughts get a larger type size in the feed
const TONES = 5;

/** stable 0..TONES-1 from the card id, so a card keeps its colour across visits. */
function toneOf(id: string) {
  let h = 0;
  for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) | 0;
  return Math.abs(h) % TONES;
}

function timeAgo(iso: string): string {
  const mins = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} min ago`;
  const h = Math.round(mins / 60);
  if (h < 24) return `${h} h ago`;
  const d = Math.round(h / 24);
  return d === 1 ? "last night" : `${d} nights ago`;
}

function CardView({ card, fresh, onReport, variant = "canvas" }: Props) {
  const [menu, toggleMenu] = useCardMenu(card.id);
  const feed = variant === "feed";
  const big = feed && !card.image && card.text.length <= BIG_TEXT_MAX;

  return (
    <article
      className={`card${feed ? ` card--feed tone-${toneOf(card.id)}` : ""}${fresh ? " fresh" : ""}`}
      style={feed ? undefined : { left: card.x, top: card.y }}
      aria-label="Anonymous card"
    >
      {card.image && (
        //eslint-disable-next-line @next/next/no-img-element
        <img className="card-image" src={card.image} alt="" loading="lazy" draggable={false} />
      )}
      <p className={`card-text${big ? " card-text--big" : ""}`}>{card.text}</p>
      <footer className="card-meta">
        <time dateTime={card.created_at}>{timeAgo(card.created_at)}</time>
        <button
          className="card-more"
          aria-label="Report this card"
          aria-expanded={menu}
          onClick={toggleMenu}
        >
          ⋯
        </button>
      </footer>
      {menu && (
        <div className="report-menu" role="menu" data-no-pan>
          {REASONS.map((r) => (
            <button
              key={r.value}
              role="menuitem"
              onClick={() => {
                toggleMenu();
                onReport(card.id, r.value);
              }}
            >
              {r.label}
            </button>
          ))}
        </div>
      )}
    </article>
  );
}

export default memo(CardView);
