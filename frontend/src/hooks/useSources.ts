import { useCallback, useEffect, useState } from "react";
import { fetchSources, type SourceListItem } from "../services/api";

export function useSources(workspaceKey: string) {
  const [sources, setSources] = useState<SourceListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchSources();
      setSources(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load sources");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh, workspaceKey]);

  return { sources, loading, error, refresh };
}
