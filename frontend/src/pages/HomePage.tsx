import { useMemo, useState } from "react";
import logo from "../../Untitled_design-3-removebg-preview.png";
import {
  deleteNotebook,
  readNotebookIndex,
  readNotebookTitle,
  type NotebookIndexItem,
  writeNotebookIndex,
  writeNotebookTitle,
} from "../services/notebooks";

interface Props {
  onOpenNotebook: (id: string) => void;
  onCreateNotebook: () => void;
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

export default function HomePage({ onOpenNotebook, onCreateNotebook }: Props) {
  const [tick, setTick] = useState(0);
  const items = useMemo(() => {
    void tick;
    return readNotebookIndex();
  }, [tick]);

  const refresh = () => setTick((x) => x + 1);

  return (
    <div className="home-shell">
      <header className="home-top">
        <div className="home-brand">
          <img className="brand-logo" src={logo} alt="Contextra" />
          <span className="home-brand-name">Contextra</span>
        </div>
      </header>

      <main className="home-main">
        <section className="home-section">
          <h2 className="home-h2">Recent notebooks</h2>
          <div className="home-grid">
            <button type="button" className="home-card home-create" onClick={onCreateNotebook}>
              <div className="home-create-plus" aria-hidden>
                +
              </div>
              <div className="home-card-title">Create new notebook</div>
            </button>

            {items.map((n) => (
              <NotebookCard
                key={n.id}
                item={n}
                onOpen={() => onOpenNotebook(n.id)}
                onDelete={() => {
                  deleteNotebook(n.id);
                  refresh();
                }}
                onRename={(title) => {
                  writeNotebookTitle(n.id, title);
                  const next: NotebookIndexItem = { ...n, title, updatedAt: new Date().toISOString() };
                  const all = readNotebookIndex().map((x) => (x.id === n.id ? next : x));
                  writeNotebookIndex(all);
                  refresh();
                }}
              />
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}

function NotebookCard({
  item,
  onOpen,
  onDelete,
  onRename,
}: {
  item: NotebookIndexItem;
  onOpen: () => void;
  onDelete: () => void;
  onRename: (title: string) => void;
}) {
  const title = item.title || readNotebookTitle(item.id) || "Untitled notebook";
  return (
    <div className="home-card-wrap">
      <button type="button" className="home-card" onClick={onOpen}>
        <div className="home-card-emoji" aria-hidden>
          📔
        </div>
        <div className="home-card-title">{title}</div>
        <div className="home-card-meta">
          {formatDate(item.updatedAt)} · {item.sourceCount} source{item.sourceCount === 1 ? "" : "s"}
        </div>
      </button>

      <div className="home-card-actions">
        <button
          type="button"
          className="home-card-action"
          onClick={() => {
            const next = window.prompt("Rename notebook", item.title || "Untitled notebook");
            if (next == null) return;
            const t = next.trim();
            if (!t) return;
            onRename(t);
          }}
        >
          Edit title
        </button>
        <button
          type="button"
          className="home-card-action danger"
          onClick={() => {
            if (!window.confirm("Delete this notebook? This removes the saved chat from your browser.")) return;
            onDelete();
          }}
        >
          Delete
        </button>
      </div>
    </div>
  );
}

