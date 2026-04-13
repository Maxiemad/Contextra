/** Collapsible backend tuning tips (env vars). */
export function TipsStrip() {
  return (
    <details className="tips-strip">
      <summary className="tips-summary">
        <span className="tips-icon" aria-hidden>
          ⓘ
        </span>
        Speed & indexing tips
      </summary>
      <div className="tips-body">
        <ul>
          <li>
            <strong>Fast image uploads:</strong> in <code>backend/.env</code> set{" "}
            <code>USE_OLLAMA_VISION=false</code> to skip local vision (llava); you still get OCR if Tesseract is
            installed.
          </li>
          <li>
            <strong>Vision timeout:</strong> <code>OLLAMA_VISION_TIMEOUT_SEC=90</code> caps how long Ollama can run
            per image (CPU can be slow).
          </li>
          <li>
            <strong>API key:</strong> if <code>API_KEY</code> is set in the backend, set the same value as{" "}
            <code>VITE_API_KEY</code> in <code>frontend/.env</code> for the UI to authenticate.
          </li>
          <li>
            <strong>Links:</strong> only public <code>http(s)</code> URLs; content must be HTML or plain text (not
            PDF direct links — download and upload the file instead).
          </li>
        </ul>
      </div>
    </details>
  );
}
