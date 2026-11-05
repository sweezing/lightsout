"use client";

//feature 5 - shown when a card is withheld for a crisis indicator, and from
//the "need to talk to someone?" link at any time.

import { useEffect, useState } from "react";

import { fetchResources } from "@/lib/api";
import type { SupportResource } from "@/lib/types";

type Props = {
  message: string | null;
  resources: SupportResource[] | null;
  onClose: () => void;
};

export default function SupportPanel({ message, resources, onClose }: Props) {
  const [list, setList] = useState<SupportResource[]>(resources ?? []);

  useEffect(() => {
    if (!resources) fetchResources().then(setList);
  }, [resources]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="sheet-backdrop" onClick={onClose}>
      <section
        className="sheet support"
        role="dialog"
        aria-modal="true"
        aria-labelledby="support-title"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id="support-title" className="sheet-title">
          {message ? "Hey. We read that." : "You don't have to wait until morning"}
        </h2>
        <p className="sheet-note">
          {message ??
            "If tonight feels like too much, talking to a real person helps. These are free and confidential."}
        </p>

        <ul className="resources">
          {list.map((r) => (
            <li key={r.name}>
              <span className="resource-region">{r.region}</span>
              {r.url ? (
                <a href={r.url} target="_blank" rel="noreferrer">{r.name}</a>
              ) : (
                <strong>{r.name}</strong>
              )}
              <span className="resource-detail">{r.detail}</span>
            </li>
          ))}
        </ul>

        <div className="sheet-actions">
          <button className="button primary" onClick={onClose}>Back to the canvas</button>
        </div>
      </section>
    </div>
  );
}
