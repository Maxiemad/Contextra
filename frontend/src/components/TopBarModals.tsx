import { useEffect, useMemo, useRef, useState } from "react";
import type { ChatMessage } from "../hooks/useChat";
import { getTenantId } from "../services/api";

export type TopBarModalMode = "share" | "settings" | null;

export type NotebookAccess = "restricted" | "link";
export type PersonRole = "owner" | "editor" | "viewer";
export type OutputLanguage = "en" | "hi";

export interface SharePerson {
  id: string;
  name: string;
  email: string;
  role: PersonRole;
}

export interface ShareSettings {
  access: NotebookAccess;
  notify: boolean;
  people: SharePerson[];
}

interface Props {
  mode: TopBarModalMode;
  onClose: () => void;
  notebookId: string;
  notebookTitle: string;
  messages: ChatMessage[];
  showTips: boolean;
  onSetShowTips: (v: boolean) => void;
  share: ShareSettings;
  onSaveShare: (next: ShareSettings) => void;
}

const OUTPUT_LANG_KEY = "multimodal_rag_output_language";
const REDUCE_MOTION_KEY = "multimodal_rag_reduce_motion";

function readBool(key: string, fallback: boolean): boolean {
  try {
    const raw = localStorage.getItem(key);
    if (raw == null) return fallback;
    return raw === "1";
  } catch {
    return fallback;
  }
}

function writeBool(key: string, v: boolean) {
  try {
    localStorage.setItem(key, v ? "1" : "0");
  } catch {
    /* ignore */
  }
}

function readOutputLanguage(): OutputLanguage {
  try {
    const raw = localStorage.getItem(OUTPUT_LANG_KEY);
    if (raw === "hi") return "hi";
    return "en";
  } catch {
    return "en";
  }
}

function writeOutputLanguage(v: OutputLanguage) {
  try {
    localStorage.setItem(OUTPUT_LANG_KEY, v);
  } catch {
    /* ignore */
  }
}

function formatChatAsMarkdown(title: string, messages: ChatMessage[]): string {
  const lines: string[] = [];
  lines.push(`# ${title || "Untitled notebook"}`);
  lines.push("");
  lines.push(`Exported: ${new Date().toISOString()}`);
  lines.push("");
  for (const m of messages) {
    lines.push(`## ${m.role === "user" ? "User" : "Assistant"}`);
    lines.push("");
    lines.push(m.content.trim());
    lines.push("");
  }
  return lines.join("\n").trim() + "\n";
}

async function copyToClipboard(text: string): Promise<void> {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const ta = document.createElement("textarea");
  ta.value = text;
  ta.style.position = "fixed";
  ta.style.left = "-9999px";
  ta.style.top = "0";
  document.body.appendChild(ta);
  ta.focus();
  ta.select();
  document.execCommand("copy");
  document.body.removeChild(ta);
}

function downloadText(filename: string, contents: string) {
  const blob = new Blob([contents], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function isValidEmail(s: string): boolean {
  const t = s.trim();
  if (!t.includes("@")) return false;
  if (t.includes(" ")) return false;
  const parts = t.split("@");
  if (parts.length !== 2) return false;
  if (!parts[0] || !parts[1] || !parts[1].includes(".")) return false;
  return true;
}

function accessLabel(a: NotebookAccess): string {
  return a === "restricted" ? "Restricted" : "Anyone with the link";
}

export function TopBarModals({
  mode,
  onClose,
  notebookId,
  notebookTitle,
  messages,
  showTips,
  onSetShowTips,
  share,
  onSaveShare,
}: Props) {
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const accessSelectRef = useRef<HTMLSelectElement>(null);
  const addPeopleRef = useRef<HTMLInputElement>(null);

  const [draft, setDraft] = useState<ShareSettings>(share);
  const [peopleInput, setPeopleInput] = useState("");
  const [localErr, setLocalErr] = useState<string | null>(null);
  const [outputLang, setOutputLang] = useState<OutputLanguage>(readOutputLanguage);
  const [reduceMotion, setReduceMotion] = useState<boolean>(() => readBool(REDUCE_MOTION_KEY, false));

  const shareUrl = useMemo(() => {
    const u = new URL(window.location.href);
    u.searchParams.set("nb", notebookId);
    return u.toString();
  }, [notebookId]);
  const workspaceId = useMemo(() => getTenantId(), []);
  const chatMd = useMemo(() => formatChatAsMarkdown(notebookTitle, messages), [notebookTitle, messages]);

  useEffect(() => {
    if (!mode) return;
    setStatus(null);
    setLocalErr(null);
    setPeopleInput("");
    setBusy(false);
    setDraft(share);
    setOutputLang(readOutputLanguage());
    setReduceMotion(readBool(REDUCE_MOTION_KEY, false));
    const t = window.setTimeout(() => {
      if (mode === "share") addPeopleRef.current?.focus();
      if (mode === "settings") accessSelectRef.current?.blur(); // no-op safety
    }, 0);
    return () => window.clearTimeout(t);
  }, [mode, share]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && mode && !busy) onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [busy, mode, onClose]);

  if (!mode) return null;

  return (
    <div
      className="modal-overlay"
      role="presentation"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget && !busy) onClose();
      }}
    >
      <div
        className="modal-card"
        role="dialog"
        aria-modal="true"
        aria-labelledby="topbar-modal-title"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="modal-head">
          <h2 id="topbar-modal-title">
            {mode === "share" ? `Share "${notebookTitle || "Untitled notebook"}"` : "Settings"}
          </h2>
          <button type="button" className="modal-close" onClick={() => !busy && onClose()} aria-label="Close">
            ×
          </button>
        </div>

        {mode === "share" && (
          <div className="modal-body">
            <div className="share-add-row">
              <input
                ref={addPeopleRef}
                className="modal-input share-add-input"
                placeholder="Add people and groups"
                value={peopleInput}
                onChange={(e) => setPeopleInput(e.target.value)}
                disabled={busy}
              />
              <button
                type="button"
                className="btn-secondary"
                disabled={busy}
                onClick={() => {
                  const raw = peopleInput.trim();
                  if (!raw) return;
                  const emails = raw
                    .split(/[,\s]+/g)
                    .map((x) => x.trim())
                    .filter(Boolean);
                  const invalid = emails.find((e) => !isValidEmail(e));
                  if (invalid) {
                    setLocalErr(`Invalid email: ${invalid}`);
                    return;
                  }
                  const now = Date.now();
                  const nextPeople = [...draft.people];
                  for (const email of emails) {
                    const exists = nextPeople.some((p) => p.email.toLowerCase() === email.toLowerCase());
                    if (exists) continue;
                    const name = email.split("@")[0] || email;
                    nextPeople.push({ id: `${now}-${email}`, name, email, role: "viewer" });
                  }
                  setDraft({ ...draft, people: nextPeople });
                  setPeopleInput("");
                  setLocalErr(null);
                }}
              >
                Add
              </button>
            </div>

            {localErr && <p className="modal-err">{localErr}</p>}

            <div className="share-section-title">
              <span>People with access</span>
              <label className="share-notify">
                <span>Notify people</span>
                <input
                  type="checkbox"
                  checked={draft.notify}
                  onChange={(e) => setDraft({ ...draft, notify: e.target.checked })}
                />
              </label>
            </div>

            <div className="share-people-list" role="list">
              {draft.people.length === 0 ? (
                <p className="modal-hint">No one added yet. Add an email above.</p>
              ) : (
                draft.people.map((p) => (
                  <div key={p.id} className="share-person" role="listitem">
                    <div className="share-avatar" aria-hidden>
                      {(p.name || p.email || "?").trim().slice(0, 1).toUpperCase()}
                    </div>
                    <div className="share-person-main">
                      <div className="share-person-name">{p.name}</div>
                      <div className="share-person-email">{p.email}</div>
                    </div>
                    <div className="share-person-actions">
                      <select
                        className="format-select share-role"
                        value={p.role}
                        onChange={(e) => {
                          const role = e.target.value as PersonRole;
                          setDraft({
                            ...draft,
                            people: draft.people.map((x) => (x.id === p.id ? { ...x, role } : x)),
                          });
                        }}
                        aria-label="Role"
                      >
                        <option value="owner">Owner</option>
                        <option value="editor">Editor</option>
                        <option value="viewer">Viewer</option>
                      </select>
                      <button
                        type="button"
                        className="link-btn"
                        onClick={() => setDraft({ ...draft, people: draft.people.filter((x) => x.id !== p.id) })}
                        title="Remove"
                      >
                        Remove
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>

            <div className="share-section-title">
              <span>Notebook Access</span>
            </div>

            <div className="share-access-row">
              <div className="share-access-left">
                <div className="share-access-label">{accessLabel(draft.access)}</div>
                <div className="share-access-hint">
                  {draft.access === "restricted"
                    ? "Only people with access can open with the link"
                    : "Anyone with the link can open (local-only demo)"}
                </div>
              </div>
              <select
                ref={accessSelectRef}
                className="format-select"
                value={draft.access}
                onChange={(e) => setDraft({ ...draft, access: e.target.value as NotebookAccess })}
                aria-label="Notebook access"
              >
                <option value="restricted">Restricted</option>
                <option value="link">Anyone with the link</option>
              </select>
            </div>

            {draft.access === "link" && (
              <label className="modal-label">
                Link
                <input className="modal-input" value={shareUrl} readOnly />
              </label>
            )}

            <div className="share-footer">
              <div className="share-footer-left">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={async () => {
                    setBusy(true);
                    setStatus(null);
                    try {
                      await copyToClipboard(shareUrl);
                      setStatus("Copied link.");
                    } finally {
                      setBusy(false);
                    }
                  }}
                >
                  Copy link
                </button>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={async () => {
                    setBusy(true);
                    setStatus(null);
                    try {
                      await copyToClipboard(chatMd);
                      setStatus("Copied chat markdown.");
                    } finally {
                      setBusy(false);
                    }
                  }}
                  disabled={messages.length === 0}
                  title={messages.length === 0 ? "No messages yet" : "Copy as markdown"}
                >
                  Copy chat
                </button>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => {
                    const safeTitle = (notebookTitle || "notebook")
                      .trim()
                      .slice(0, 60)
                      .replaceAll(/[^\w\- ]+/g, "")
                      .replaceAll(/\s+/g, "-")
                      .toLowerCase();
                    downloadText(`${safeTitle || "notebook"}-chat.md`, chatMd);
                  }}
                  disabled={messages.length === 0}
                >
                  Export .md
                </button>
              </div>
              <button
                type="button"
                className="btn-primary"
                disabled={busy}
                onClick={() => {
                  onSaveShare(draft);
                  setStatus("Saved.");
                }}
              >
                Save
              </button>
            </div>

            {status && <p className="modal-hint">{status}</p>}

            <p className="modal-hint">
              Workspace id: <code>{workspaceId}</code>
            </p>
          </div>
        )}

        {mode === "settings" && (
          <div className="modal-body">
            <div className="settings-list" role="list">
              <button
                type="button"
                className="settings-item"
                role="listitem"
                onClick={() => window.open("https://github.com/", "_blank", "noreferrer")}
              >
                <span className="settings-ico" aria-hidden>
                  ?
                </span>
                <span className="settings-label">NotebookLM Help</span>
              </button>

              <button
                type="button"
                className="settings-item"
                role="listitem"
                onClick={() => {
                  window.location.href = `mailto:?subject=${encodeURIComponent(
                    `Feedback: ${notebookTitle || "Notebook"}`,
                  )}&body=${encodeURIComponent(`Workspace: ${workspaceId}\nNotebook: ${notebookTitle}\n\n`)}`;
                }}
              >
                <span className="settings-ico" aria-hidden>
                  !
                </span>
                <span className="settings-label">Send feedback</span>
              </button>

              <div className="settings-item-row" role="listitem">
                <div className="settings-item-left">
                  <span className="settings-ico" aria-hidden>
                    🌐
                  </span>
                  <span className="settings-label">Output Language</span>
                </div>
                <select
                  className="format-select settings-select"
                  value={outputLang}
                  onChange={(e) => {
                    const v = (e.target.value === "hi" ? "hi" : "en") as OutputLanguage;
                    setOutputLang(v);
                    writeOutputLanguage(v);
                  }}
                  aria-label="Output language"
                >
                  <option value="en">English</option>
                  <option value="hi">Hindi</option>
                </select>
              </div>

              <div className="settings-item-row" role="listitem">
                <div className="settings-item-left">
                  <span className="settings-ico" aria-hidden>
                    ⓘ
                  </span>
                  <span className="settings-label">Show tips strip</span>
                </div>
                <label className="settings-toggle" aria-label="Show tips strip">
                  <input type="checkbox" checked={showTips} onChange={(e) => onSetShowTips(e.target.checked)} />
                </label>
              </div>

              <div className="settings-item-row" role="listitem">
                <div className="settings-item-left">
                  <span className="settings-ico" aria-hidden>
                    ◐
                  </span>
                  <span className="settings-label">Device</span>
                </div>
                <label className="settings-toggle" aria-label="Reduce motion">
                  <span className="settings-muted">Reduce motion</span>
                  <input
                    type="checkbox"
                    checked={reduceMotion}
                    onChange={(e) => {
                      const v = e.target.checked;
                      setReduceMotion(v);
                      writeBool(REDUCE_MOTION_KEY, v);
                      document.documentElement.classList.toggle("reduce-motion", v);
                    }}
                  />
                </label>
              </div>
            </div>

            <div className="modal-actions">
              <button type="button" className="btn-secondary" onClick={onClose}>
                Done
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

