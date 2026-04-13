import { useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import type { ChatMessage } from "../hooks/useChat";
import { AddSourceModals, type ModalMode } from "./AddSourceModals";
import { UPLOAD_ACCEPT } from "./FileUpload";

interface Props {
  messages: ChatMessage[];
  pending: boolean;
  error: string | null;
  onSend: (text: string, format?: string) => void;
  sourceCount: number;
  onAddFiles: (files: File[]) => void;
  addFilesDisabled: boolean;
  ingestStatus: string | null;
  onIngestPastedText: (text: string, title?: string) => Promise<void>;
  onIngestUrl: (url: string) => Promise<void>;
}

export function ChatPanel({
  messages,
  pending,
  error,
  onSend,
  sourceCount,
  onAddFiles,
  addFilesDisabled,
  ingestStatus,
  onIngestPastedText,
  onIngestUrl,
}: Props) {
  const [input, setInput] = useState("");
  const [format, setFormat] = useState<string>("");
  const [dragOver, setDragOver] = useState(false);
  const [modal, setModal] = useState<ModalMode>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const showHero = messages.length === 0;

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);
    if (addFilesDisabled) return;
    const list = e.dataTransfer.files;
    if (list?.length) onAddFiles(Array.from(list));
  };

  return (
    <section className="panel chat-panel">
      <div className="panel-header chat-panel-header">
        <div>
          <h2>Chat</h2>
          <div className="panel-sub">Ask anything — answers cite your sources</div>
        </div>
        <select
          className="format-select"
          value={format}
          onChange={(e) => setFormat(e.target.value)}
          aria-label="Response format"
        >
          <option value="">Default</option>
          <option value="bullets">Bullet points</option>
          <option value="table">Table when useful</option>
          <option value="sections">Sections</option>
        </select>
      </div>

      <div className="chat-scroll">
        {showHero && (
          <div className="chat-hero">
            <h3 className="chat-hero-title">
              Turn your sources into
              <span className="chat-hero-gradient"> answers</span>
            </h3>
            <p className="chat-hero-lead">
              Upload PDFs, images, docs, or video — then ask questions or use Studio shortcuts. Retrieval stays
              grounded; references show on the right.
            </p>

            <input
              ref={fileRef}
              type="file"
              multiple
              accept={UPLOAD_ACCEPT}
              hidden
              disabled={addFilesDisabled}
              onChange={(e) => {
                const list = e.target.files;
                if (list?.length) onAddFiles(Array.from(list));
                e.target.value = "";
              }}
            />

            <div
              className={`chat-dropzone${dragOver && !addFilesDisabled ? " chat-dropzone-active" : ""}`}
              onDragEnter={(e) => {
                e.preventDefault();
                if (!addFilesDisabled) setDragOver(true);
              }}
              onDragLeave={(e) => {
                e.preventDefault();
                const rt = e.relatedTarget as Node | null;
                if (rt && (e.currentTarget as HTMLElement).contains(rt)) return;
                setDragOver(false);
              }}
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleDrop}
            >
              <p className="chat-dropzone-title">Drop files to add sources</p>
              <p className="chat-dropzone-muted">PDF · images · docx · txt · video</p>
              <div className="chat-pill-row">
                <button
                  type="button"
                  className="chat-pill"
                  disabled={addFilesDisabled}
                  onClick={() => fileRef.current?.click()}
                >
                  <span className="chat-pill-ico" aria-hidden>
                    ↑
                  </span>
                  Upload files
                </button>
                <button
                  type="button"
                  className="chat-pill"
                  disabled={addFilesDisabled}
                  onClick={() => setModal("link")}
                >
                  <span className="chat-pill-ico" aria-hidden>
                    🔗
                  </span>
                  Links
                </button>
                <button
                  type="button"
                  className="chat-pill"
                  disabled={addFilesDisabled}
                  onClick={() => setModal("paste")}
                >
                  <span className="chat-pill-ico" aria-hidden>
                    ✎
                  </span>
                  Paste text
                </button>
              </div>
            </div>
          </div>
        )}

        {messages.map((m) => (
          <div key={m.id} className={`bubble ${m.role}`}>
            {m.role === "assistant" ? (
              <ReactMarkdown>{m.content}</ReactMarkdown>
            ) : (
              <p>{m.content}</p>
            )}
          </div>
        ))}
        {pending && (
          <div className="bubble assistant thinking-bubble">
            <span className="thinking-dots" aria-hidden>
              <span />
              <span />
              <span />
            </span>
            Thinking…
          </div>
        )}
        {error && <div className="error-banner chat-inline-err">{error}</div>}
        {!showHero && (
          <div className="chat-quick-add">
            <span className="chat-quick-add-label">Add source:</span>
            <button type="button" className="link-btn" disabled={addFilesDisabled} onClick={() => setModal("paste")}>
              Paste text
            </button>
            <button type="button" className="link-btn" disabled={addFilesDisabled} onClick={() => setModal("link")}>
              Link
            </button>
          </div>
        )}
      </div>

      <div className="chat-footer-bar">
        <span className="chat-footer-count">
          {sourceCount} source{sourceCount === 1 ? "" : "s"}
        </span>
        <span className="chat-footer-mid">{ingestStatus || "Upload sources to unlock Studio tools"}</span>
      </div>

      <form
        className="chat-input-row"
        onSubmit={(e) => {
          e.preventDefault();
          if (!input.trim() || pending) return;
          onSend(input, format || undefined);
          setInput("");
        }}
      >
        <textarea
          rows={2}
          placeholder={sourceCount ? "Ask a question about your sources…" : "Add sources first, then ask anything…"}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              if (!input.trim() || pending) return;
              onSend(input, format || undefined);
              setInput("");
            }
          }}
        />
        <button type="submit" className="btn-primary chat-send-btn" disabled={pending}>
          Send
        </button>
      </form>

      <AddSourceModals
        mode={modal}
        onClose={() => setModal(null)}
        busy={addFilesDisabled}
        onPasteSubmit={onIngestPastedText}
        onUrlSubmit={onIngestUrl}
      />
    </section>
  );
}
