import { useState } from "react";
import { getTenantId, setTenantId } from "../services/api";

interface Props {
  onApplied: (tenantId: string) => void;
}

/** Matches backend: 1–64 chars, letters, digits, _, -, . */
const TENANT_PATTERN = /^[\w.-]{1,64}$/;

export function WorkspaceBar({ onApplied }: Props) {
  const [value, setValue] = useState(() => getTenantId());
  const [err, setErr] = useState<string | null>(null);

  const apply = () => {
    const v = value.trim();
    if (!TENANT_PATTERN.test(v)) {
      setErr("Use 1–64 characters: letters, digits, _, -, .");
      return;
    }
    setErr(null);
    try {
      setTenantId(v);
      onApplied(v);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Invalid workspace");
    }
  };

  return (
    <div className="workspace-bar">
      <label htmlFor="ws-id">Workspace</label>
      <input
        id="ws-id"
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && apply()}
        title="Sent as X-Tenant-ID — isolated data per workspace"
        spellCheck={false}
        autoComplete="off"
      />
      <button type="button" className="btn-secondary btn-compact" onClick={apply}>
        Apply
      </button>
      {err && <span className="workspace-err">{err}</span>}
    </div>
  );
}
