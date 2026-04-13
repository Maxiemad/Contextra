import { useCallback, useEffect, useMemo, useState } from "react";
import HomePage from "./pages/HomePage";
import NotebookPage from "./pages/NotebookPage";

export default function App() {
  const [urlState, setUrlState] = useState(() => window.location.search);

  useEffect(() => {
    document.title = "Contextra";
    const onPop = () => setUrlState(window.location.search);
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  const params = useMemo(() => new URLSearchParams(urlState), [urlState]);
  const notebookId = params.get("nb");

  const navigateTo = useCallback((next: URLSearchParams) => {
    const qs = next.toString();
    const url = qs ? `?${qs}` : window.location.pathname;
    window.history.pushState({}, "", url);
    setUrlState(window.location.search);
  }, []);

  const openNotebook = useCallback(
    (id: string) => {
      const next = new URLSearchParams(window.location.search);
      next.set("nb", id);
      navigateTo(next);
    },
    [navigateTo],
  );

  const goHome = useCallback(() => {
    const next = new URLSearchParams(window.location.search);
    next.delete("nb");
    navigateTo(next);
  }, [navigateTo]);

  const createNotebook = useCallback(() => {
    openNotebook(crypto.randomUUID());
  }, [openNotebook]);

  if (!notebookId) {
    return <HomePage onOpenNotebook={openNotebook} onCreateNotebook={createNotebook} />;
  }

  return <NotebookPage notebookId={notebookId} onRequestHome={goHome} onRequestNewNotebook={createNotebook} />;
}
