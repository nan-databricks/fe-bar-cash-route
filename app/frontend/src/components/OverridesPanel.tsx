import { useEffect, useState } from "react";
import { Send } from "lucide-react";
import type { RouteExecution } from "../types";
import { fetchOverrides, postOverride, type DataSource, type DispatchOverride } from "../data/api";

const ACTIONS: DispatchOverride["action"][] = ["SKIP", "ADD", "RESEQUENCE", "EMERGENCY"];
const ACTION_COLOR: Record<string, string> = {
  SKIP: "#94a3b8",
  ADD: "#22c55e",
  RESEQUENCE: "#38bdf8",
  EMERGENCY: "#ef4444",
};

/** Dispatcher overrides for a route, persisted to Lakebase public.dispatch_overrides. */
export default function OverridesPanel({ exec, serviceDate }: { exec: RouteExecution; serviceDate: string }) {
  const nodes = exec.stops.filter((s) => s.code !== "DEPOT");
  const [rows, setRows] = useState<DispatchOverride[]>([]);
  const [source, setSource] = useState<DataSource | "">("");
  const [nodeId, setNodeId] = useState(nodes[0]?.code ?? "");
  const [action, setAction] = useState<DispatchOverride["action"]>("SKIP");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  const load = async () => {
    const r = await fetchOverrides(exec.routeId);
    if (r) {
      setRows(r.overrides);
      setSource(r.source);
    }
  };

  useEffect(() => {
    setNodeId(nodes[0]?.code ?? "");
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [exec.routeId]);

  const submit = async () => {
    if (!nodeId) return;
    setBusy(true);
    setMsg("");
    try {
      const r = await postOverride({
        service_date: serviceDate,
        route_id: exec.routeId,
        node_id: nodeId,
        action,
        reason: reason || null,
        created_by: null,
      });
      setMsg(`Saved override #${r.override.override_id} → ${r.source === "lakebase" ? "Lakebase" : "mock store"}`);
      setReason("");
      await load();
    } catch (e) {
      setMsg(String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="panel">
      <div className="panel-head">
        <h2>Dispatch Overrides · {exec.routeId}</h2>
        <span className={`source-chip ${source === "lakebase" ? "live" : ""}`}>
          {source === "lakebase" ? "Lakebase · public.dispatch_overrides" : source ? "mock store" : "…"}
        </span>
      </div>
      <div className="panel-body">
        <div className="override-form">
          <label>
            Node
            <select className="select-inline" value={nodeId} onChange={(e) => setNodeId(e.target.value)}>
              {nodes.map((s) => (
                <option key={s.code} value={s.code}>
                  {s.seq}. {s.code} · {s.location}
                </option>
              ))}
            </select>
          </label>
          <label>
            Action
            <select className="select-inline" value={action} onChange={(e) => setAction(e.target.value as DispatchOverride["action"])}>
              {ACTIONS.map((a) => (
                <option key={a} value={a}>{a}</option>
              ))}
            </select>
          </label>
          <label className="grow">
            Reason
            <input
              className="select-inline"
              value={reason}
              placeholder="e.g. site closed, police escort delayed…"
              onChange={(e) => setReason(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submit()}
            />
          </label>
          <button className="btn sm primary" onClick={submit} disabled={busy || !nodeId}>
            <Send size={13} /> {busy ? "Saving…" : "Submit override"}
          </button>
        </div>
        {msg && <div className="hint" style={{ marginTop: 8 }}>{msg}</div>}
        <table className="branch-table" style={{ marginTop: 10 }}>
          <thead>
            <tr>
              <th>#</th>
              <th>Node</th>
              <th>Action</th>
              <th>Reason</th>
              <th>By</th>
              <th>At</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr><td colSpan={6} style={{ color: "var(--muted)" }}>No overrides for this route yet.</td></tr>
            )}
            {rows.map((o) => (
              <tr key={o.override_id}>
                <td style={{ color: "var(--muted)" }}>{o.override_id}</td>
                <td style={{ fontWeight: 600 }}>{o.node_id}</td>
                <td><span style={{ color: ACTION_COLOR[o.action] ?? "inherit", fontWeight: 700 }}>{o.action}</span></td>
                <td>{o.reason ?? "—"}</td>
                <td style={{ color: "var(--muted)" }}>{o.created_by ?? "—"}</td>
                <td style={{ color: "var(--muted)" }}>{o.created_at ? o.created_at.replace("T", " ").slice(0, 16) : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
