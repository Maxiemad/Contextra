import { useCallback, useEffect, useMemo, useState } from "react";
import { ChatPanel } from "../components/ChatPanel";
import { FileUpload } from "../components/FileUpload";
import { SourcesPanel } from "../components/SourcesPanel";
import { StudioPanel } from "../components/StudioPanel";
import { TipsStrip } from "../components/TipsStrip";
import { TopBarModals, type ShareSettings, type TopBarModalMode } from "../components/TopBarModals";
import { WorkspaceBar } from "../components/WorkspaceBar";
import { useChat } from "../hooks/useChat";
import { useSources } from "../hooks/useSources";
import { readNotebookTitle, upsertNotebookIndexItem, writeNotebookTitle } from "../services/notebooks";
import logo from "../../Untitled_design-3-removebg-preview.png";
import {
  deleteSource,
  getTenantId,
  uploadFilesAsync,
  uploadTextAsync,
  uploadUrlAsync,
  waitForIngestionJobs,
  type AsyncUploadAccepted,
} from "../services/api";

const SHOW_TIPS_KEY = "multimodal_rag_show_tips";
const SHARE_PREFIX = "multimodal_rag_share:";

function readShowTips(): boolean {
  try {
    const raw = localStorage.getItem(SHOW_TIPS_KEY);
    if (raw == null) return true;
    return raw === "1";
  } catch {
    return true;
  }
}

function defaultShareSettings(): ShareSettings {
  return {
    access: "restricted",
    notify: true,
    people: [
      // Local-only demo default owner
      { id: "owner", name: "You", email: "you@example.com", role: "owner" },
    ],
  };
}

function readShareSettings(notebookId: string): ShareSettings {
  try {
    const raw = localStorage.getItem(`${SHARE_PREFIX}${notebookId}`);
    if (!raw) return defaultShareSettings();
    const parsed = JSON.parse(raw) as Partial<ShareSettings> | null;
    if (!parsed || typeof parsed !== "object") return defaultShareSettings();
    const access = parsed.access === "link" ? "link" : "restricted";
    const notify = typeof parsed.notify === "boolean" ? parsed.notify : true;
    const people = Array.isArray(parsed.people) ? parsed.people : [];
    return { access, notify, people: people as ShareSettings["people"] };
  } catch {
    return defaultShareSettings();
  }
}

interface Props {
  notebookId: string;
  onRequestHome: () => void;
  onRequestNewNotebook: () => void;
}

export default function NotebookPage({ notebookId, onRequestHome, onRequestNewNotebook }: Props) {
  const [workspaceKey, setWorkspaceKey] = useState(() => getTenantId());
  const [notebookTitle, setNotebookTitle] = useState(() => readNotebookTitle(notebookId));
  const [topModal, setTopModal] = useState<TopBarModalMode>(null);
  const [showTips, setShowTips] = useState(readShowTips);
  const [share, setShare] = useState<ShareSettings>(() => readShareSettings(notebookId));
  const { sources, loading, error: srcErr, refresh } = useSources(workspaceKey);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [uploading, setUploading] = useState(false);
  const [ingestStatus, setIngestStatus] = useState<string | null>(null);
  const [uploadErr, setUploadErr] = useState<string | null>(null);

  useEffect(() => {
    writeNotebookTitle(notebookId, notebookTitle);
  }, [notebookId, notebookTitle]);

  useEffect(() => {
    try {
      localStorage.setItem(SHOW_TIPS_KEY, showTips ? "1" : "0");
    } catch {
      /* ignore */
    }
  }, [showTips]);

  useEffect(() => {
    try {
      localStorage.setItem(`${SHARE_PREFIX}${notebookId}`, JSON.stringify(share));
    } catch {
      /* ignore */
    }
  }, [notebookId, share]);

  const scopeIds = useMemo(() => {
    if (selectedIds.size === 0) return null;
    return Array.from(selectedIds);
  }, [selectedIds]);

  const { messages, pending, error: chatErr, send, clear, attachNotebook } = useChat(scopeIds);

  useEffect(() => {
    // On notebook switch: reload title/share and attach chat storage
    setNotebookTitle(readNotebookTitle(notebookId));
    setShare(readShareSettings(notebookId));
    setSelectedIds(new Set());
    clear();
    attachNotebook(notebookId);
  }, [attachNotebook, clear, notebookId]);

  const onWorkspaceApplied = useCallback(
    (_id: string) => {
      setWorkspaceKey(_id);
      clear();
    },
    [clear],
  );

  const lastCitations = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      const m = messages[i];
      if (m.role === "assistant" && m.citations?.length) return m.citations;
    }
    return [];
  }, [messages]);

  const ingestAfterAccepted = useCallback(async (accepted: AsyncUploadAccepted[]) => {
    if (!accepted.length) return;
    const ids = accepted.map((a) => a.job_id);
    setUploading(false);
    setIngestStatus(`Indexing ${accepted.length} source(s)…`);
    await waitForIngestionJobs(ids, {
      intervalMs: 500,
      onUpdate: (j) => setIngestStatus(`${j.source_name}: ${j.status}…`),
    });
    setIngestStatus(null);
    await refresh();
  }, [refresh]);

  const onUpload = async (files: File[]) => {
    setUploading(true);
    setIngestStatus(null);
    setUploadErr(null);
    try {
      const accepted = await uploadFilesAsync(files);
      await ingestAfterAccepted(accepted);
    } catch (e) {
      setUploadErr(e instanceof Error ? e.message : "Upload failed");
      setIngestStatus(null);
    } finally {
      setUploading(false);
    }
  };

  const onIngestPastedText = async (text: string, title?: string) => {
    setUploading(true);
    setUploadErr(null);
    setIngestStatus(null);
    try {
      const accepted = await uploadTextAsync(text, title);
      await ingestAfterAccepted(accepted);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to add text";
      setUploadErr(msg);
      setIngestStatus(null);
      throw e;
    } finally {
      setUploading(false);
    }
  };

  const onIngestUrl = async (url: string) => {
    setUploading(true);
    setUploadErr(null);
    setIngestStatus(null);
    try {
      const accepted = await uploadUrlAsync(url);
      await ingestAfterAccepted(accepted);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to add URL";
      setUploadErr(msg);
      setIngestStatus(null);
      throw e;
    } finally {
      setUploading(false);
    }
  };

  useEffect(() => {
    upsertNotebookIndexItem({
      id: notebookId,
      title: notebookTitle || "Untitled notebook",
      updatedAt: new Date().toISOString(),
      sourceCount: sources.length,
      messageCount: messages.length,
    });
  }, [messages.length, notebookId, notebookTitle, sources.length]);

  const toggle = useCallback((id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const selectAll = useCallback(() => {
    setSelectedIds(new Set(sources.map((s) => s.document_id)));
  }, [sources]);

  const clearSelection = useCallback(() => setSelectedIds(new Set()), []);

  const onDeleteSource = useCallback(
    async (documentId: string) => {
      setUploadErr(null);
      try {
        await deleteSource(documentId);
        setSelectedIds((prev) => {
          const next = new Set(prev);
          next.delete(documentId);
          return next;
        });
        await refresh();
      } catch (e) {
        setUploadErr(e instanceof Error ? e.message : "Could not delete source");
      }
    },
    [refresh],
  );

  const sourceCount = sources.length;

  return (
    <div className="app-shell">
      <header className="top-bar notebook-top">
        <div className="top-bar-left">
          <button type="button" className="brand-home" onClick={onRequestHome} aria-label="Home">
            <img className="brand-logo" src={logo} alt="Contextra" />
            <span className="brand-name">Contextra</span>
          </button>
          <input
            type="text"
            className="notebook-title-input"
            value={notebookTitle}
            onChange={(e) => setNotebookTitle(e.target.value)}
            spellCheck={false}
            maxLength={120}
            aria-label="Notebook title"
          />
        </div>
        <div className="top-bar-center">
          {ingestStatus && <span className="ingest-pill ingest-pill-animated">{ingestStatus}</span>}
        </div>
        <div className="top-bar-right">
          <WorkspaceBar onApplied={onWorkspaceApplied} />
          <button type="button" className="btn-top-text" onClick={onRequestNewNotebook} title="New notebook">
            New chat
          </button>
          <FileUpload onFiles={onUpload} disabled={uploading} />
          <button
            type="button"
            className="btn-top-ghost"
            onClick={() => setTopModal("share")}
            title="Copy link or export chat"
          >
            Share
          </button>
          <button
            type="button"
            className="btn-top-icon"
            title="Settings"
            aria-label="Settings"
            onClick={() => setTopModal("settings")}
          >
            ⚙
          </button>
        </div>
      </header>
      {(srcErr || uploadErr) && (
        <div className="error-banner global">{srcErr || uploadErr}</div>
      )}
      {showTips && <TipsStrip />}
      <main className="three-col">
        <SourcesPanel
          sources={sources}
          loading={loading}
          selectedIds={selectedIds}
          onToggle={toggle}
          onSelectAll={selectAll}
          onClearSelection={clearSelection}
          onDelete={onDeleteSource}
          onAddFiles={onUpload}
          addDisabled={uploading}
        />
        <ChatPanel
          messages={messages}
          pending={pending}
          error={chatErr}
          onSend={send}
          sourceCount={sourceCount}
          onAddFiles={onUpload}
          addFilesDisabled={uploading}
          ingestStatus={ingestStatus}
          onIngestPastedText={onIngestPastedText}
          onIngestUrl={onIngestUrl}
        />
        <StudioPanel
          citations={lastCitations}
          hasSources={sourceCount > 0}
          onRunPrompt={send}
          pending={pending}
        />
      </main>

      <TopBarModals
        mode={topModal}
        onClose={() => setTopModal(null)}
        notebookId={notebookId}
        notebookTitle={notebookTitle}
        messages={messages}
        showTips={showTips}
        onSetShowTips={setShowTips}
        share={share}
        onSaveShare={setShare}
      />
    </div>
  );
}
