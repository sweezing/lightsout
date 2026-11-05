"use client";

//feature 3 - the nightly prompt. one question a night (21:00-05:00 in the
//reader's own time zone). answering just opens the normal composer; the
//answer becomes an ordinary anonymous card, not a labelled reply.

import { useEffect, useState } from "react";

import { fetchPrompt } from "@/lib/api";
import type { Prompt } from "@/lib/types";

const REFRESH_MS = 10 * 60 * 1000;

export default function PromptBanner({
  onAnswer,
  inline = false,
}: {
  onAnswer: (text: string) => void;
  /** in the feed the question sits at the top of the scroll instead of floating. */
  inline?: boolean;
}) {
  const [prompt, setPrompt] = useState<Prompt | null>(null);
  const [hidden, setHidden] = useState(false);

  useEffect(() => {
    let alive = true;
    const load = () =>
      fetchPrompt()
        .then((p) => alive && setPrompt(p))
        .catch(() => undefined);
    load();
    const t = setInterval(load, REFRESH_MS);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, []);

  if (!prompt?.text || hidden) return null;

  return (
    <aside className={`prompt${inline ? " prompt--inline" : ""}`} aria-label="Tonight's question">
      <span className="prompt-label">{prompt.in_window ? "Tonight" : "Last night"}</span>
      <p className="prompt-text">{prompt.text}</p>
      <div className="prompt-actions">
        <button className="button small" onClick={() => onAnswer(prompt.text!)}>Answer</button>
        <button className="link-button" aria-label="Hide tonight's question" onClick={() => setHidden(true)}>✕</button>
      </div>
    </aside>
  );
}
