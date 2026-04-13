import { useEffect, useRef, useState } from "react";

export type ModalMode = "paste" | "link" | null;

interface Props {
  mode: ModalMode;
  onClose: () => void;
  busy: boolean;
  onPasteSubmit: (text: string, title?: string) => Promise<void>;
  onUrlSubmit: (url: string) => Promise<void>;
}

export function AddSourceModals({ mode, onClose, busy, onPasteSubmit, onUrlSubmit }: Props) {
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [url, setUrl] = useState("");
  const [localErr, setLocalErr] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const pasteAreaRef = useRef<HTMLTextAreaElement>(null);
  const urlInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!mode) return;
    setLocalErr(null);
    if (mode === "paste") {
      setText("");
      setTitle("");
    } else {
      setUrl("");
    }
  }, [mode]);

  useEffect(() => {
    if (mode === "paste") pasteAreaRef.current?.focus();
    if (mode === "link") urlInputRef.current?.focus();
  }, [mode]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && mode && !submitting) onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [mode, onClose, submitting]);

  if (!mode) return null;

  const overlay = (
    <div
      className="modal-overlay"
      role="presentation"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget && !submitting) onClose();
      }}
    >
      <div
        className="modal-card"
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="modal-head">
          <h2 id="modal-title">{mode === "paste" ? "Paste text" : "Add from link"}</h2>
          <button type="button" className="modal-close" onClick={() => !submitting && onClose()} aria-label="Close">
            ×
          </button>
        </div>

        {mode === "paste" && (
          <form
            className="modal-body"
            onSubmit={async (e) => {
              e.preventDefault();
              const t = text.trim();
              if (!t) {
                setLocalErr("Enter some text.");
                return;
              }
              setLocalErr(null);
              setSubmitting(true);
              try {
                await onPasteSubmit(t, title.trim() || undefined);
                onClose();
              } catch (err) {
                setLocalErr(err instanceof Error ? err.message : "Failed");
              } finally {
                setSubmitting(false);
              }
            }}
          >
            <label className="modal-label">
              Title (optional)
              <input
                type="text"
                className="modal-input"
                placeholder="e.g. Meeting notes"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                disabled={busy || submitting}
              />
            </label>
            <label className="modal-label">
              Text
              <textarea
                ref={pasteAreaRef}
                className="modal-textarea"
                rows={12}
                placeholder="Paste or type content to index as a source…"
                value={text}
                onChange={(e) => setText(e.target.value)}
                disabled={busy || submitting}
              />
            </label>
            {localErr && <p className="modal-err">{localErr}</p>}
            <div className="modal-actions">
              <button type="button" className="btn-secondary" onClick={() => !submitting && onClose()}>
                Cancel
              </button>
              <button type="submit" className="btn-primary" disabled={busy || submitting}>
                {submitting ? "Adding…" : "Add source"}
              </button>
            </div>
          </form>
        )}

        {mode === "link" && (
          <form
            className="modal-body"
            onSubmit={async (e) => {
              e.preventDefault();
              const u = url.trim();
              if (!u.startsWith("http://") && !u.startsWith("https://")) {
                setLocalErr("URL must start with https:// or http://");
                return;
              }
              setLocalErr(null);
              setSubmitting(true);
              try {
                await onUrlSubmit(u);
                onClose();
              } catch (err) {
                setLocalErr(err instanceof Error ? err.message : "Failed");
              } finally {
                setSubmitting(false);
              }
            }}
          >
            <p className="modal-hint">
              Public pages only (HTML or plain text). Localhost and private networks are blocked on the server.
            </p>
            <label className="modal-label">
              URL
              <input
                ref={urlInputRef}
                type="url"
                className="modal-input"
                placeholder="https://example.com/article"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                disabled={busy || submitting}
                autoComplete="url"
              />
            </label>
            {localErr && <p className="modal-err">{localErr}</p>}
            <div className="modal-actions">
              <button type="button" className="btn-secondary" onClick={() => !submitting && onClose()}>
                Cancel
              </button>
              <button type="submit" className="btn-primary" disabled={busy || submitting}>
                {submitting ? "Fetching…" : "Add source"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );

  return overlay;
}
