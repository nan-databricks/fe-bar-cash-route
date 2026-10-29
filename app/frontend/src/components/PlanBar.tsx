import { Banknote, Gauge, Ruler, ShieldAlert, Timer, Truck, Wallet } from "lucide-react";
import type { PlanType, RouteSummaryRow } from "../data/api";
import { thb } from "../data/format";

/** BASELINE vs OPTIMIZED toggle. */
export function PlanToggle({ value, onChange }: { value: PlanType; onChange: (p: PlanType) => void }) {
  return (
    <div className="plan-toggle" role="tablist" aria-label="Plan type">
      {(["BASELINE", "OPTIMIZED"] as PlanType[]).map((p) => (
        <button
          key={p}
          role="tab"
          aria-selected={value === p}
          className={`plan-opt ${value === p ? "active" : ""} ${p.toLowerCase()}`}
          onClick={() => onChange(p)}
        >
          {p === "BASELINE" ? "Baseline (fixed cycle)" : "Optimized (CVRP-TW)"}
        </button>
      ))}
    </div>
  );
}

function delta(cur: number, other: number | undefined, lowerIsBetter: boolean) {
  if (other === undefined || other === 0) return null;
  const pct = ((cur - other) / Math.abs(other)) * 100;
  if (Math.abs(pct) < 0.05) return { text: "± 0%", good: true };
  const good = lowerIsBetter ? pct < 0 : pct > 0;
  return { text: `${pct > 0 ? "▲" : "▼"} ${Math.abs(pct).toFixed(1)}%`, good };
}

/** Summary KPIs from gold_route_summary for the selected plan, with delta vs the other plan. */
export function PlanKpis({ rows, plan, source }: { rows: RouteSummaryRow[]; plan: PlanType; source?: string }) {
  const cur = rows.find((r) => r.plan_type === plan);
  const other = rows.find((r) => r.plan_type !== plan && r.service_date === cur?.service_date);
  if (!cur) return null;
  const vs = plan === "OPTIMIZED" ? "vs baseline" : "vs optimized";
  const items = [
    { icon: <Banknote size={18} color="#f2a900" />, label: "CIT cost / day", value: thb(cur.cost_thb), d: delta(cur.cost_thb, other?.cost_thb, true) },
    { icon: <Ruler size={18} color="#38bdf8" />, label: "Distance", value: `${cur.km.toLocaleString("en-US", { maximumFractionDigits: 0 })} km`, d: delta(cur.km, other?.km, true) },
    { icon: <Truck size={18} color="#a855f7" />, label: "Vans used", value: `${cur.vehicles_used} / 30`, d: delta(cur.vehicles_used, other?.vehicles_used, true) },
    { icon: <Wallet size={18} color="#22c55e" />, label: "Idle cash", value: thb(cur.idle_cash_thb), d: delta(cur.idle_cash_thb, other?.idle_cash_thb, true) },
    { icon: <ShieldAlert size={18} color="#ef4444" />, label: "Cash-out risk nodes", value: String(cur.cashout_risk_nodes), d: delta(cur.cashout_risk_nodes, other?.cashout_risk_nodes, true) },
    { icon: <Gauge size={18} color="#22c55e" />, label: "SLA", value: `${cur.sla_pct.toFixed(1)}%`, d: delta(cur.sla_pct, other?.sla_pct, false) },
    { icon: <Timer size={18} color="#38bdf8" />, label: "Crew hours", value: `${cur.duration_hr.toLocaleString("en-US", { maximumFractionDigits: 0 })} h`, d: delta(cur.duration_hr, other?.duration_hr, true) },
  ];
  return (
    <div className="plan-kpis">
      {items.map((it) => (
        <div key={it.label} className={`kpi plan-kpi ${plan === "OPTIMIZED" ? "opt" : "base"}`}>
          <span className="icon">{it.icon}</span>
          <div className="k-label">{it.label}</div>
          <div className="k-value">{it.value}</div>
          {it.d && (
            <div className="k-delta">
              <span className={it.d.good ? "up" : "down"}>{it.d.text}</span>
              <span className="kd-label">{vs}</span>
            </div>
          )}
        </div>
      ))}
      <div className="plan-kpi-foot">
        {cur.service_date} · {cur.routes} routes · {cur.stops} stops · source: {source === "unity_catalog" ? "UC gold_route_summary" : "mock"}
      </div>
    </div>
  );
}
