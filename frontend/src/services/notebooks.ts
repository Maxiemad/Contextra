export interface NotebookIndexItem {
  id: string;
  title: string;
  updatedAt: string; // ISO
  sourceCount: number;
  messageCount: number;
}

const INDEX_KEY = "contextra_notebooks_index";
const TITLE_PREFIX = "contextra_notebook_title:";
const MESSAGES_PREFIX = "contextra_notebook_messages:";
const SHARE_PREFIX = "multimodal_rag_share:"; // existing key used elsewhere

export function getNotebookTitleKey(id: string) {
  return `${TITLE_PREFIX}${id}`;
}

export function getNotebookMessagesKey(id: string) {
  return `${MESSAGES_PREFIX}${id}`;
}

function safeParse<T>(raw: string | null): T | null {
  if (!raw) return null;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

export function readNotebookIndex(): NotebookIndexItem[] {
  try {
    const parsed = safeParse<unknown>(localStorage.getItem(INDEX_KEY));
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(Boolean) as NotebookIndexItem[];
  } catch {
    return [];
  }
}

export function writeNotebookIndex(items: NotebookIndexItem[]) {
  try {
    localStorage.setItem(INDEX_KEY, JSON.stringify(items));
  } catch {
    /* ignore */
  }
}

export function upsertNotebookIndexItem(item: NotebookIndexItem) {
  const all = readNotebookIndex();
  const idx = all.findIndex((x) => x.id === item.id);
  const next = idx === -1 ? [item, ...all] : [item, ...all.filter((x) => x.id !== item.id)];
  next.sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
  writeNotebookIndex(next);
}

export function deleteNotebook(id: string) {
  const next = readNotebookIndex().filter((x) => x.id !== id);
  writeNotebookIndex(next);
  try {
    localStorage.removeItem(getNotebookTitleKey(id));
    localStorage.removeItem(getNotebookMessagesKey(id));
    localStorage.removeItem(`${SHARE_PREFIX}${id}`);
  } catch {
    /* ignore */
  }
}

export function readNotebookTitle(id: string): string {
  try {
    const t = localStorage.getItem(getNotebookTitleKey(id));
    return t?.trim() || "Untitled notebook";
  } catch {
    return "Untitled notebook";
  }
}

export function writeNotebookTitle(id: string, title: string) {
  try {
    localStorage.setItem(getNotebookTitleKey(id), title);
  } catch {
    /* ignore */
  }
}

