import { useEffect, useState } from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from "recharts";
import type { RouteExecution } from "../types";
import type { RouteTrackSummary } from "../data/routeExec";
import type { PlanType, RouteSummaryRow } from "../data/api";
import { thb } from "../data/format";
import FleetMap from "./FleetMap";
import { PlanKpis, PlanToggle } from "./PlanBar";

const STATUS_COLOR: Record<string, string> = {
  "On Track": "#22c55e",
  Delayed: "#f59e0b",
  "At Risk": "#ef4444",
};

export default function RouteTrackingPage({
  execs,
  summary,
  planType,
  onPlanChange,
  summaryRows,
  summarySource,
  onOpenDetail,
}: {
  execs: RouteExecution[];
  summary: RouteTrackSummary;
  planType: PlanType;
  onPlanChange: (p: PlanType) => void;
  summaryRows: RouteSummaryRow[];
  summarySource?: string;
  onOpenDetail: (routeId: string) => void;
}) {
  const [selectedRouteId, setSelectedRouteId] = useState<string>(() => execs[0]?.routeId ?? "");
  useEffect(() => {
    if (execs.length && !execs.some((e) => e.routeId === selectedRouteId)) {
      setSelectedRouteId(execs[0].routeId);
    }
  }, [execs, selectedRouteId]);

  const donut = [
    { name: "On Track", value: summary.onTrack, color: "#22c55e" },
    { name: "Delayed", value: summary.delayed, color: "#f59e0b" },
    { name: "At Risk", value: summary.atRisk, color: "#ef4444" },
  ].filter((d) => d.value > 0);

  const base = summaryRows.find((r) => r.plan_type === "BASELINE");
  const opt = summaryRows.find((r) => r.plan_type === "OPTIMIZED");
  const cmp = base && opt
    ? [
        { metric: "CIT Cost / day", before: thb(base.cost_thb), after: thb(opt.cost_thb), imp: pct(base.cost_thb, opt.cost_thb) },
        { metric: "Total Distance", before: `${Math.round(base.km).toLocaleString()} km`, after: `${Math.round(opt.km).toLocaleString()} km`, imp: pct(base.km, opt.km) },
        { metric: "Crew Hours", before: `${Math.round(base.duration_hr)} h`, after: `${Math.round(opt.duration_hr)} h`, imp: pct(base.duration_hr, opt.duration_hr) },
        { metric: "Vans Used", before: String(base.vehicles_used), after: String(opt.vehicles_used), imp: pct(base.vehicles_used, opt.vehicles_used) },
        { metric: "Idle Cash", before: thb(base.idle_cash_thb), after: thb(opt.idle_cash_thb), imp: pct(base.idle_cash_thb, opt.idle_cash_thb) },
        { metric: "Cash-out Risk Nodes", before: String(base.cashout_risk_nodes), after: String(opt.cashout_risk_nodes), imp: pct(base.cashout_risk_nodes, opt.cashout_risk_nodes) },
        { metric: "SLA Achievement", before: `${base.sla_pct}%`, after: `${opt.sla_pct}%`, imp: `▲ ${(opt.sla_pct - base.sla_pct).toFixed(1)} pts` },
      ]
    : [];

  return (
    <div className="track-page">
      <div className="page-toolbar plan-bar">
        <span className="pt-title">Route Tracking · {planType === "OPTIMIZED" ? "Optimized plan" : "Baseline plan"}</span>
        <PlanToggle value={planType} onChange={onPlanChange} />
      </div>

      <PlanKpis rows={summaryRows} plan={planType} source={summarySource} />

      <div className="track-split route-split">
        <div className="panel">
          <div className="panel-head">
            <h2>Route Tracking Map</h2>
            <span className="hint">
              {summary.totalRoutes} routes · {selectedRouteId || "—"} highlighted · click a line to select
            </span>
          </div>
          <div style={{ height: 460 }}>
            <FleetMap execs={execs} selectedId={selectedRouteId} onSelect={setSelectedRouteId} />
          </div>
        </div>

        <div className="panel">
          <div className="panel-head">
            <h2>Route Summary</h2>
            <span className="hint">live status</span>
          </div>
          <div className="panel-body">
            <div style={{ position: "relative" }}>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie data={donut} dataKey="value" nameKey="name" innerRadius="62%" outerRadius="85%" paddingAngle={2} stroke="none">
                    {donut.map((d, i) => (
                      <Cell key={i} fill={d.color} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ background: "#0f1728", border: "1px solid #26314a", borderRadius: 8, fontSize: 12 }} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                </PieChart>
              </ResponsiveContainer>
              <div className="donut-center">
                <div className="dc-value">{summary.totalRoutes}</div>
                <div className="dc-label">Total Routes</div>
              </div>
            </div>
            <div className="route-status-rows">
              <StatusRow color="#22c55e" label="On Track" value={summary.onTrack} total={summary.totalRoutes} />
              <StatusRow color="#f59e0b" label="Delayed" value={summary.delayed} total={summary.totalRoutes} />
              <StatusRow color="#ef4444" label="At Risk" value={summary.atRisk} total={summary.totalRoutes} />
            </div>
          </div>
        </div>
      </div>

      <div className="track-split route-split">
        <div className="panel">
          <div className="panel-head">
            <h2>Active Routes</h2>
            <span className="hint">click a route to highlight · truck opens detail</span>
          </div>
          <div className="panel-body" style={{ padding: 0 }}>
            <table className="branch-table">
              <thead>
                <tr>
                  <th>Route</th>
                  <th>Truck</th>
                  <th>Status</th>
                  <th className="num">Stops</th>
                  <th className="num">Distance</th>
                  <th className="num">ETA Return</th>
                </tr>
              </thead>
              <tbody>
                {execs.map((e) => (
                  <tr
                    key={e.routeId}
                    style={{
                      cursor: "pointer",
                      background: e.routeId === selectedRouteId ? "rgba(56,189,248,0.08)" : undefined,
                    }}
                    onClick={() => setSelectedRouteId(e.routeId)}
                  >
                    <td>
                      <div style={{ fontWeight: 600, display: "flex", alignItems: "center", gap: 6 }}>
                        <span className="status-dot" style={{ background: e.color }} />
                        {e.routeId}
                        {e.routeId === selectedRouteId && <span className="badge-custom">on map</span>}
                      </div>
                      <div style={{ color: "var(--muted)", fontSize: 10 }}>{e.label}</div>
                    </td>
                    <td>
                      <button
                        type="button"
                        className="btn sm ghost"
                        onClick={(ev) => {
                          ev.stopPropagation();
                          onOpenDetail(e.routeId);
                        }}
                      >
                        {e.truckId}
                      </button>
                    </td>
                    <td><span style={{ color: STATUS_COLOR[e.status], fontWeight: 600, fontSize: 11 }}>● {e.status}</span></td>
                    <td className="num">{e.completed}/{e.totalStops}</td>
                    <td className="num">{e.distanceKm} km</td>
                    <td className="num">{e.etaReturn}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="panel">
          <div className="panel-head">
            <h2>Baseline vs Optimized (per day)</h2>
            <span className="hint">gold_route_summary · fixed cycle → CVRP-TW</span>
          </div>
          <div className="panel-body" style={{ padding: 0 }}>
            <table className="branch-table">
              <thead>
                <tr>
                  <th>Metric</th>
                  <th className="num">Baseline</th>
                  <th className="num">Optimized</th>
                  <th className="num">Improvement</th>
                </tr>
              </thead>
              <tbody>
                {cmp.map((r) => (
                  <tr key={r.metric}>
                    <td style={{ fontWeight: 600 }}>{r.metric}</td>
                    <td className="num" style={{ color: "var(--muted)" }}>{r.before}</td>
                    <td className="num">{r.after}</td>
                    <td className="num" style={{ color: r.imp === "—" ? "var(--muted)" : "#22c55e", fontWeight: 600 }}>
                      {r.imp !== "—" && !String(r.imp).startsWith("▲") && !String(r.imp).startsWith("▼") ? `▼ ${r.imp}` : r.imp}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

function pct(before: number, after: number): string {
  if (!before) return "0%";
  return `${Math.round(((before - after) / before) * 1000) / 10}%`;
}

function StatusRow({ color, label, value, total }: { color: string; label: string; value: number; total: number }) {
  const p = total ? Math.round((value / total) * 100) : 0;
  return (
    <div className="status-row">
      <span className="status-dot" style={{ background: color }} />
      <span className="sr-label">{label}</span>
      <span className="sr-value">{value} ({p}%)</span>
    </div>
  );
}
