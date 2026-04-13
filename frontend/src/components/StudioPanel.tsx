import { useEffect, useState } from "react";
import type { Citation } from "../services/api";

const STUDIO_TOOLS: Array<{
  id: string;
  label: string;
  hint: string;
  prompt: string;
  format?: string;
  icon: string;
}> = [
  {
    id: "summary",
    label: "Summary",
    hint: "Overview of themes",
    prompt:
      "Give a clear, concise summary of the main themes and facts across my sources. Cite which source each idea comes from.",
    format: "sections",
    icon: "◆",
  },
  {
    id: "keypoints",
    label: "Key points",
    hint: "Bulleted takeaways",
    prompt:
      "Extract the most important bullet points from my sources. Use markdown bullets and cite sources.",
    format: "bullets",
    icon: "▸",
  },
  {
    id: "study",
    label: "Study guide",
    hint: "Sections + terms",
    prompt:
      "Create a study guide from my sources: sections with headings, key terms in bold, and short explanations. Include citations.",
    format: "sections",
    icon: "☰",
  },
  {
    id: "quiz",
    label: "Quiz",
    hint: "Practice questions",
    prompt:
      "Generate 5 study questions based only on my sources (mix short answer and multiple choice). Provide an answer key at the end. Cite sources.",
    icon: "?",
  },
  {
    id: "compare",
    label: "Compare",
    hint: "Contrast ideas",
    prompt:
      "Compare and contrast the main ideas or arguments across my sources. Note agreements and disagreements. Use citations.",
    format: "sections",
    icon: "⇄",
  },
  {
    id: "glossary",
    label: "Glossary",
    hint: "Terms defined",
    prompt:
      "Build a glossary of important terms, names, and concepts from my sources. One short definition per term and cite where it appears.",
    format: "bullets",
    icon: "α",
  },
  {
    id: "table",
    label: "Data table",
    hint: "Structured facts",
    prompt:
      "If my sources contain comparable facts, figures, or entities, present them in a markdown table. Explain the table briefly and cite sources.",
    format: "table",
    icon: "⊞",
  },
  {
    id: "timeline",
    label: "Timeline",
    hint: "Chronology",
    prompt:
      "If dates or sequences appear in my sources, present a chronological timeline. If not enough temporal info, say so briefly. Cite sources.",
    format: "bullets",
    icon: "⌁",
  },
];

interface Props {
  citations: Citation[];
  hasSources: boolean;
  onRunPrompt: (prompt: string, format?: string) => void;
  pending: boolean;
}

export function StudioPanel({ citations, hasSources, onRunPrompt, pending }: Props) {
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    setExpanded(null);
  }, [citations]);

  return (
    <aside className="panel refs-panel studio-panel">
      <div className="panel-header studio-header">
        <div>
          <h2>Studio</h2>
          <div className="panel-sub">One-tap prompts on your sources</div>
        </div>
      </div>

      <div className="studio-banner">
        <span className="studio-banner-dot" aria-hidden />
        Grounded answers use the same retrieval as chat — pick a tool or type in the center.
      </div>

      <div className="studio-grid-wrap">
        <div className="studio-grid">
          {STUDIO_TOOLS.map((t) => (
            <button
              key={t.id}
              type="button"
              className="studio-card"
              disabled={!hasSources || pending}
              title={!hasSources ? "Add sources first" : t.hint}
              onClick={() => onRunPrompt(t.prompt, t.format)}
            >
              <span className="studio-card-icon" aria-hidden>
                {t.icon}
              </span>
              <span className="studio-card-label">{t.label}</span>
              <span className="studio-card-hint">{t.hint}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="studio-section-title">
        <span>References</span>
        <span className="studio-section-meta">{citations.length ? `${citations.length} excerpts` : "After you chat"}</span>
      </div>

      {citations.length === 0 && (
        <div className="studio-refs-empty">
          <div className="studio-refs-empty-icon" aria-hidden>
            ◇
          </div>
          <p>
            Send a message or use a Studio tool — grounded excerpts from your sources appear here with traceability.
          </p>
        </div>
      )}

      <ol className="citation-list studio-citation-list">
        {citations.map((c, i) => (
          <li key={`${c.chunk_id}-${i}`} className="citation-card">
            <div className="citation-head">
              <span className="badge">{i + 1}</span>
              <span className="citation-title">{c.source_name}</span>
              <span className="citation-score">{(c.similarity_score * 100).toFixed(1)}%</span>
            </div>
            <details
              open={expanded === c.chunk_id}
              onToggle={(e) => {
                if ((e.target as HTMLDetailsElement).open) setExpanded(c.chunk_id);
              }}
            >
              <summary>Exact excerpt</summary>
              <pre className="excerpt">{c.excerpt}</pre>
            </details>
          </li>
        ))}
      </ol>
    </aside>
  );
}
