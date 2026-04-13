import { useMemo, useRef, useState } from "react";
import type { SourceListItem } from "../services/api";
import { UPLOAD_ACCEPT } from "./FileUpload";

interface Props {
  sources: SourceListItem[];
  loading: boolean;
  selectedIds: Set<string>;
  onToggle: (id: string) => void;
  onSelectAll: () => void;
  onClearSelection: () => void;
  onDelete?: (id: string) => void;
  /** Wired from NotebookPage — enables drag-and-drop and empty-state file picker */
  onAddFiles?: (files: File[]) => void;
  addDisabled?: boolean;
}

export function SourcesPanel({
  sources,
  loading,
  selectedIds,
  onToggle,
  onSelectAll,
  onClearSelection,
  onDelete,
  onAddFiles,
  addDisabled,
}: Props) {
  const [dragOver, setDragOver] = useState(false);
  const [query, setQuery] = useState("");
  const emptyInputRef = useRef<HTMLInputElement>(null);

  const canAdd = Boolean(onAddFiles) && !addDisabled;

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return sources;
    return sources.filter((s) => s.source_name.toLowerCase().includes(q));
  }, [sources, query]);

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (canAdd) setDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const rt = e.relatedTarget as Node | null;
    if (rt && (e.currentTarget as HTMLElement).contains(rt)) return;
    setDragOver(false);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);
    if (!canAdd || !onAddFiles) return;
    const list = e.dataTransfer.files;
    if (list?.length) onAddFiles(Array.from(list));
  };

  return (
    <aside
      className={`panel sources-panel${dragOver && canAdd ? " drop-target" : ""}`}
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      <div className="panel-header sources-header">
        <div>
          <h2>Sources</h2>
          <div className="panel-sub">Click to scope retrieval · drag to add</div>
        </div>
        <div className="panel-actions">
          <button type="button" className="link-btn" onClick={onSelectAll}>
            All
          </button>
          <button type="button" className="link-btn" onClick={onClearSelection}>
            Clear
          </button>
        </div>
      </div>
      <div className="sources-search-wrap">
        <input
          type="search"
          className="sources-search"
          placeholder="Filter sources…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          aria-label="Filter sources"
        />
      </div>
      {loading && (
        <p className="muted small" style={{ padding: "0 1rem" }}>
          Loading…
        </p>
      )}
      {!loading && sources.length === 0 && (
        <div className="sources-empty">
          <input
            ref={emptyInputRef}
            type="file"
            multiple
            accept={UPLOAD_ACCEPT}
            hidden
            disabled={!canAdd}
            onChange={(e) => {
              const list = e.target.files;
              if (list?.length && onAddFiles) onAddFiles(Array.from(list));
              e.target.value = "";
            }}
          />
          <div className="sources-empty-icon" aria-hidden>
            ⧉
          </div>
          <p>
            <strong>Drop files here</strong> or choose below
            <br />
            <span className="small muted">pdf · images · docx · txt · video</span>
          </p>
          {onAddFiles && (
            <button
              type="button"
              className="btn-secondary sources-empty-browse"
              disabled={addDisabled}
              onClick={() => emptyInputRef.current?.click()}
            >
              Choose files
            </button>
          )}
        </div>
      )}
      <ul className="source-list">
        {filtered.map((s) => {
          const active = selectedIds.has(s.document_id);
          return (
            <li key={s.document_id} className="source-row">
              <button
                type="button"
                className={`source-item ${active ? "active" : ""}`}
                onClick={() => onToggle(s.document_id)}
                title="Click to include/exclude from retrieval scope"
              >
                <span className="source-name">{s.source_name}</span>
                <span className="source-meta">
                  {s.source_type}
                  {active ? " · in scope" : ""}
                </span>
              </button>
              {onDelete && (
                <button
                  type="button"
                  className="source-delete"
                  title="Remove from notebook"
                  aria-label={`Remove ${s.source_name}`}
                  onClick={(e) => {
                    e.stopPropagation();
                    onDelete(s.document_id);
                  }}
                >
                  ×
                </button>
              )}
            </li>
          );
        })}
      </ul>
    </aside>
  );
}
