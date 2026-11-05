"use client";

//feature 1, step 1 of 2: write. step 2 (place) happens on the canvas.
//no sign-up, no email, no confirmation screen.

import { useEffect, useRef, useState } from "react";

export type Draft = { text: string; image: File | null };

const MAX = 280;
const MAX_IMAGE_BYTES = 5 * 1024 * 1024;

type Props = {
  draft: Draft;
  onChange: (d: Draft) => void;
  placeholder: string | null;
  error: string | null;
  /** feed mode posts straight away; canvas mode goes on to the placing step. */
  submitLabel?: string;
  busy?: boolean;
  onNext: () => void;
  onClose: () => void;
};

export default function Composer({
  draft, onChange, placeholder, error, onNext, onClose,
  submitLabel = "Place it on the canvas →", busy = false,
}: Props) {
  const area = useRef<HTMLTextAreaElement>(null);
  const [imageError, setImageError] = useState<string | null>(null);
  const [preview, setPreview] = useState<string | null>(null);

  useEffect(() => area.current?.focus(), []);

  useEffect(() => {
    if (!draft.image) {
      setPreview(null);
      return;
    }
    const url = URL.createObjectURL(draft.image);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [draft.image]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const text = draft.text;
  const left = MAX - text.length;
  const canGo = text.trim().length > 0 && left >= 0;

  const pickImage = (file: File | null) => {
    setImageError(null);
    if (!file) return onChange({ ...draft, image: null });
    if (!["image/jpeg", "image/png"].includes(file.type)) {
      setImageError("Only JPEG or PNG.");
      return;
    }
    if (file.size > MAX_IMAGE_BYTES) {
      setImageError("Images can be up to 5 MB.");
      return;
    }
    onChange({ ...draft, image: file });
  };

  return (
    <div className="sheet-backdrop" onClick={onClose}>
      <section
        className="sheet"
        role="dialog"
        aria-modal="true"
        aria-labelledby="composer-title"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id="composer-title" className="sheet-title">What's keeping you up?</h2>
        <p className="sheet-note">No name, no account. Nobody will know it was you.</p>

        <textarea
          ref={area}
          className="composer-text"
          value={text}
          maxLength={MAX}
          rows={5}
          placeholder={placeholder ?? "Write it down and let it go…"}
          onChange={(e) => onChange({ ...draft, text: e.target.value })}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey) && canGo) onNext();
          }}
        />

        <div className="composer-row">
          <label className="image-pick">
            <input
              type="file"
              accept="image/jpeg,image/png"
              onChange={(e) => pickImage(e.target.files?.[0] ?? null)}
            />
            {draft.image ? "Change photo" : "Add a photo"}
          </label>
          <span className={`counter${left < 20 ? " low" : ""}`} aria-live="polite">
            {left}
          </span>
        </div>

        {preview && (
          <div className="image-preview">
            {/*eslint-disable-next-line @next/next/no-img-element */}
            <img src={preview} alt="Selected photo" />
            <button className="link-button" onClick={() => pickImage(null)}>Remove</button>
            <p className="sheet-note">Location and camera details are removed before it's saved.</p>
          </div>
        )}

        {(imageError || error) && <p className="form-error" role="alert">{imageError ?? error}</p>}

        <div className="sheet-actions">
          <button className="button ghost" onClick={onClose}>Not now</button>
          <button className="button primary" disabled={!canGo || busy} onClick={onNext}>
            {busy ? "Posting…" : submitLabel}
          </button>
        </div>
      </section>
    </div>
  );
}
