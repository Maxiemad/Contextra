import { useCallback, useEffect, useState } from "react";
import { queryApi, type Citation, type QueryResponse } from "../services/api";
import { getNotebookMessagesKey } from "../services/notebooks";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  retrieved?: QueryResponse["retrieved_chunks_preview"];
}

function id() {
  return crypto.randomUUID();
}

export function useChat(selectedDocIds: string[] | null) {
  const [notebookId, setNotebookId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const attachNotebook = useCallback((id: string) => {
    setNotebookId(id);
    setMessages(() => {
      try {
        const raw = localStorage.getItem(getNotebookMessagesKey(id));
        if (!raw) return [];
        const parsed = JSON.parse(raw) as ChatMessage[];
        return Array.isArray(parsed) ? parsed : [];
      } catch {
        return [];
      }
    });
    setError(null);
    setPending(false);
  }, []);

  useEffect(() => {
    if (!notebookId) return;
    try {
      localStorage.setItem(getNotebookMessagesKey(notebookId), JSON.stringify(messages));
    } catch {
      /* ignore */
    }
  }, [messages, notebookId]);

  const send = useCallback(
    async (text: string, responseFormat?: string) => {
      const trimmed = text.trim();
      if (!trimmed) return;
      setError(null);
      setPending(true);
      const userMsg: ChatMessage = { id: id(), role: "user", content: trimmed };
      setMessages((m) => [...m, userMsg]);
      try {
        const res = await queryApi(trimmed, {
          document_ids:
            selectedDocIds && selectedDocIds.length > 0 ? selectedDocIds : undefined,
          response_format: responseFormat,
          top_k: 6,
        });
        const assistant: ChatMessage = {
          id: id(),
          role: "assistant",
          content: res.answer,
          citations: res.citations,
          retrieved: res.retrieved_chunks_preview,
        };
        setMessages((m) => [...m, assistant]);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Query failed");
      } finally {
        setPending(false);
      }
    },
    [selectedDocIds],
  );

  const clear = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return { messages, pending, error, send, clear, attachNotebook };
}
