import { useMemo, useState } from "react";
import {
  Banknote,
  PiggyBank,
  Truck,
  TrendingDown,
  Building2,
  CheckCircle2,
  Gauge,
  Filter,
  MoreVertical,
  Calendar,
  MapPin,
} from "lucide-react";
import { PieChart, Pie, Cell, ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";
import type { AppConfig, BranchTrack, Machine, PlanBundle, RouteExecution } from "../types";
import type { ExecMetrics } from "../types";
import type { RouteTrackSummary } from "../data/routeExec";
import { buildExecutiveMetrics } from "../data/executiveOverview";
import { deriveMachine, generateBranchTracks } from "../data/tracking";
import { loadMachines } from "../data/machineStore";
import { thb } from "../data/format";
import HealthMap, { type MapPoint } from "./HealthMap";

function thbB(n: number): string {
  if (n >= 1_000_000_000) return `THB ${(n / 1_000_000_000).toFixed(2)}B`;
  if (n >= 1_000_000) return `THB ${(n / 1_000_000).toFixed(2)}M`;
  return thb(n, false);
}

function Sparkline({ data, color }: { data: number[]; color: string }) {
  const w = 72;
  const h = 28;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const pts = data
    .map((v, i) => {
      const x = (i / (data.length - 1)) * w;
      const y = h - ((v - min) / range) * (h - 4) - 2;
      return `${x},${y}`;
    })
    .join(" ");
  return (
    <svg width={w} height={h} className="eo-spark">
      <polyline points={pts} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

interface Delta {
  text: string;
  dir: "up" | "down" | "flat";
  good: boolean;
}

function EoKpi({
  icon,
  label,
  value,
  delta,
  spark,
  tone,
  compareLabel = "vs last week",
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  delta?: Delta;
  spark?: number[];
  tone?: "green" | "amber" | "danger";
  compareLabel?: string;
}) {
  const arrow = delta ? (delta.dir === "up" ? "▲" : delta.dir === "down" ? "▼" : "●") : "";
  return (
    <div className={`eo-kpi ${tone ?? ""}`}>
      <div className="eo-kpi-top">
        <span className="eo-kpi-icon">{icon}</span>
        {spark && <Sparkline data={spark} color={tone === "danger" ? "#ef4444" : tone === "green" ? "#22c55e" : "#38bdf8"} />}
      </div>
      <div className="eo-kpi-label">{label}</div>
      <div className="eo-kpi-value">{value}</div>
      {delta && (
        <div className="eo-kpi-delta">
          <span className={delta.good ? "good" : "bad"}>
            {arrow} {delta.text}
          </span>
          <span className="eo-kpi-vs">{compareLabel}</span>
        </div>
      )}
    </div>
  );
}

const RISK_COLOR: Record<string, string> = {
  "Very High": "#ef4444",
  High: "#f97316",
  Medium: "#eab308",
  Low: "#22c55e",
};

const STATUS_COLOR: Record<string, string> = {
  "On Track": "#22c55e",
  Delayed: "#f59e0b",
  "At Risk": "#ef4444",
};

export default function ExecutiveOverviewPage({
  config,
  plan,
  metrics,
  execs,
  routeSummary,
  machinesOverride,
  branchTracksOverride,
}: {
  config: AppConfig;
  plan: PlanBundle;
  metrics: ExecMetrics;
  execs: RouteExecution[];
  routeSummary: RouteTrackSummary;
  machinesOverride?: Machine[];
  branchTracksOverride?: BranchTrack[];
}) {
  const [mapLayers, setMapLayers] = useState({ machines: true, branches: true });

  const machines = useMemo(
    () => machinesOverride ?? loadMachines().map(deriveMachine),
    [machinesOverride]
  );
  const branchTracks = useMemo(
    () => branchTracksOverride ?? generateBranchTracks(config),
    [branchTracksOverride, config]
  );
  const em = useMemo(
    () => buildExecutiveMetrics(config, plan, metrics, execs, routeSummary, machines),
    [config, plan, metrics, execs, routeSummary, machines]
  );

  const machinePoints = useMemo<MapPoint[]>(
    () =>
      machines.map((m) => ({
        id: `machine-${m.id}`,
        kind: "machine" as const,
        lat: m.lat,
        lng: m.lng,
        health: m.health,
        title: `${m.id} · ${m.location}`,
        rows: [
          ["Type", "Machine"],
          ["Current", thb(m.currentCash)],
          ["Predicted EOD", thb(m.predictedEod)],
          ["Action", m.action],
          ["Risk", m.riskLevel],
        ],
      })),
    [machines]
  );

  const branchPoints = useMemo<MapPoint[]>(
    () =>
      branchTracks.map((b) => ({
        id: `branch-${b.code}`,
        kind: "branch" as const,
        lat: b.lat,
        lng: b.lng,
        health: b.health,
        emphasize: b.emergency,
        title: `${b.name} · ${b.code}`,
        rows: [
          ["Type", "Branch"],
          ["Current cash", thb(b.currentCash)],
          ["Deposit", thb(b.deposit)],
          ["Withdraw", thb(b.withdraw)],
          ["Action", b.action],
        ],
      })),
    [branchTracks]
  );

  const visibleMapPoints = useMemo(() => {
    const points: MapPoint[] = [];
    if (mapLayers.machines) points.push(...machinePoints);
    if (mapLayers.branches) points.push(...branchPoints);
    return points;
  }, [mapLayers, machinePoints, branchPoints]);

  const toggleMapLayer = (layer: "machines" | "branches") => {
    setMapLayers((prev) => {
      const next = { ...prev, [layer]: !prev[layer] };
      // Keep at least one layer on — empty map is never useful.
      if (!next.machines && !next.branches) return prev;
      return next;
    });
  };

  const machineCount = machinePoints.length;
  const branchCount = branchPoints.length;
  const visibleCount = visibleMapPoints.length;

  const donut = [
    { name: "On Track", value: em.routeStatus.onTrack, color: STATUS_COLOR["On Track"] },
    { name: "Delayed", value: em.routeStatus.delayed, color: STATUS_COLOR.Delayed },
    { name: "At Risk", value: em.routeStatus.atRisk, color: STATUS_COLOR["At Risk"] },
  ].filter((d) => d.value > 0);

  const glance = [
    { label: "Planned Deliveries", value: String(em.today.plannedDeliveries), delta: "+12%", dir: "up" as const },
    { label: "Planned Pickups", value: String(em.today.plannedPickups), delta: "+8%", dir: "up" as const },
    { label: "Planned Mixed (Del + Pick)", value: String(em.today.plannedMixed), delta: "+5%", dir: "up" as const },
    { label: "Total Stops", value: String(em.today.totalStops), delta: null, dir: null },
    { label: "Total Distance", value: `${em.today.totalDistanceKm.toLocaleString()} km`, delta: "−11%", dir: "down" as const },
    { label: "Total Duration", value: `${em.today.totalDurationH} hrs`, delta: "−9%", dir: "down" as const },
  ];

  return (
    <div className="overview-page">
      <div className="overview-toolbar">
        <div className="overview-filters">
          <div className="eo-filter">
            <Calendar size={14} />
            <span>Date</span>
            <span className="eo-filter-val">{config.params.planDate}</span>
          </div>
          <div className="eo-filter">
            <MapPin size={14} />
            <span>Region</span>
            <span className="eo-filter-val">{config.params.region}</span>
          </div>
        </div>
        <div className="overview-actions">
          <span className="eo-refresh">Source: Unity Catalog</span>
          <button type="button" className="btn sm ghost" disabled>
            <Filter size={14} /> Filters
          </button>
          <button type="button" className="icon-btn" aria-label="More" disabled>
            <MoreVertical size={16} />
          </button>
        </div>
      </div>

      <div className="eo-kpi-row">
        <EoKpi
          icon={<Banknote size={18} color="#38bdf8" />}
          label="Total Cash Managed"
          value={thbB(em.totalCashManaged)}
          delta={{ text: "8%", dir: "up", good: true }}
          spark={[82, 85, 88, 90, 92, 95, 100]}
        />
        <EoKpi
          icon={<PiggyBank size={18} color="#f59e0b" />}
          label="Idle Cash"
          value={thbB(em.idleCash)}
          delta={{ text: "15%", dir: "down", good: true }}
          tone="amber"
        />
        <EoKpi
          icon={<Truck size={18} color="#38bdf8" />}
          label="CIT Cost (MTD)"
          value={thbB(em.citCostMtd)}
          delta={{ text: "10%", dir: "down", good: true }}
          compareLabel="vs last month"
        />
        <EoKpi
          icon={<TrendingDown size={18} color="#ef4444" />}
          label="Cash Out Risk"
          value={`${em.cashOutRiskMachines} Machines`}
          delta={{ text: "42%", dir: "up", good: false }}
          tone="danger"
          spark={[4, 6, 7, 9, 10, 11, em.cashOutRiskMachines]}
        />
        <EoKpi
          icon={<Building2 size={18} color="#ef4444" />}
          label="Branch Risk"
          value={`${em.branchRisk} Branches`}
          delta={{ text: "22%", dir: "up", good: false }}
          tone="danger"
          spark={[3, 4, 5, 6, 7, 8, em.branchRisk]}
        />
        <EoKpi
          icon={<CheckCircle2 size={18} color="#22c55e" />}
          label="Route SLA"
          value={`${em.routeSla}%`}
          delta={{ text: "2.1pp", dir: "up", good: true }}
          tone="green"
          spark={[94.2, 95.1, 95.8, 96.4, 97.2, 97.9, em.routeSla]}
        />
        <EoKpi
          icon={<Gauge size={18} color="#38bdf8" />}
          label="Vehicle Utilization"
          value={`${em.vehicleUtilization}%`}
          delta={{ text: "5.4pp", dir: "up", good: true }}
          spark={em.utilization24h.map((d) => d.pct)}
        />
      </div>

      <div className="overview-main">
        <div className="panel overview-map-panel">
          <div className="panel-head">
            <h2>Cash Health Map (Machines &amp; Branches)</h2>
            <span className="hint">{visibleCount} shown</span>
          </div>
          <div className="overview-map-wrap">
            <div className="eo-map-viewby" role="group" aria-label="Map layers">
              <span className="eo-map-viewby-label">View by</span>
              <span className="eo-map-viewby-hint">Select one or both</span>
              <div className="eo-map-viewby-btns">
                <button
                  type="button"
                  className={`eo-toggle eo-layer-toggle ${mapLayers.machines ? "on" : ""}`}
                  onClick={() => toggleMapLayer("machines")}
                  aria-pressed={mapLayers.machines}
                >
                  <span className={`eo-layer-check ${mapLayers.machines ? "checked" : ""}`} aria-hidden>
                    {mapLayers.machines ? "✓" : ""}
                  </span>
                  <span className="eo-layer-swatch machine" aria-hidden />
                  Machines
                  <span className="eo-layer-count">{machineCount}</span>
                </button>
                <button
                  type="button"
                  className={`eo-toggle eo-layer-toggle ${mapLayers.branches ? "on" : ""}`}
                  onClick={() => toggleMapLayer("branches")}
                  aria-pressed={mapLayers.branches}
                >
                  <span className={`eo-layer-check ${mapLayers.branches ? "checked" : ""}`} aria-hidden>
                    {mapLayers.branches ? "✓" : ""}
                  </span>
                  <span className="eo-layer-swatch branch" aria-hidden />
                  Branches
                  <span className="eo-layer-count">{branchCount}</span>
                </button>
              </div>
            </div>
            <HealthMap points={visibleMapPoints} showKindLegend />
          </div>
        </div>

        <div className="panel overview-glance">
          <div className="panel-head">
            <h2>Today At A Glance</h2>
          </div>
          <div className="panel-body eo-glance-list">
            {glance.map((g) => (
              <div className="eo-glance-row" key={g.label}>
                <span className="eo-glance-label">{g.label}</span>
                <span className="eo-glance-val">
                  {g.value}
                  {g.delta && (
                    // Decreases are always red (ops signal), increases green —
                    // independent of whether the change is "good" for cost.
                    <span
                      className={g.dir === "down" ? "decrease" : "increase"}
                      style={{ marginLeft: 8, fontSize: 11 }}
                    >
                      {g.delta}
                    </span>
                  )}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="panel overview-routes">
          <div className="panel-head">
            <h2>Route Status</h2>
          </div>
          <div className="panel-body eo-route-donut">
            <div className="eo-donut-side">
              {donut.map((d) => (
                <div className="eo-status-row" key={d.name}>
                  <span className="status-dot" style={{ background: d.color }} />
                  <span>{d.name}</span>
                  <span className="eo-status-pct">
                    {em.routeStatus.total ? Math.round((d.value / em.routeStatus.total) * 1000) / 10 : 0}%
                  </span>
                </div>
              ))}
            </div>
            <div className="eo-donut-chart">
              <ResponsiveContainer width="100%" height={160}>
                <PieChart>
                  <Pie data={donut} dataKey="value" nameKey="name" innerRadius="58%" outerRadius="82%" paddingAngle={2} stroke="none">
                    {donut.map((d) => (
                      <Cell key={d.name} fill={d.color} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
              <div className="eo-donut-center">
                <strong>{em.routeStatus.total}</strong>
                <span>Total Routes</span>
              </div>
            </div>
          </div>
        </div>

        <div className="panel overview-risk">
          <div className="panel-head">
            <h2>Cash Out Risk (Top 10 Machines)</h2>
          </div>
          <div className="panel-body" style={{ padding: 0, overflowX: "auto" }}>
            <table className="branch-table eo-risk-table">
              <thead>
                <tr>
                  <th>Machine</th>
                  <th>Location</th>
                  <th className="num">Predicted Cash</th>
                  <th>Risk</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {em.topCashOutRisk.map((m) => (
                  <tr key={m.id}>
                    <td style={{ fontWeight: 600 }}>{m.id}</td>
                    <td>{m.location}</td>
                    <td className="num">{thb(m.predictedCash)}</td>
                    <td>
                      <span className="eo-risk-pill" style={{ color: RISK_COLOR[m.risk], borderColor: `${RISK_COLOR[m.risk]}55`, background: `${RISK_COLOR[m.risk]}18` }}>
                        {m.risk}
                      </span>
                    </td>
                    <td>
                      <button type="button" className="eo-action-btn">{m.action}</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="panel overview-util">
          <div className="panel-head">
            <h2>Vehicle Utilization</h2>
            <span className="hint">24h trend</span>
          </div>
          <div className="panel-body">
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={em.utilization24h} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="var(--border-soft)" strokeDasharray="4 4" vertical={false} />
                <XAxis dataKey="hour" tick={{ fill: "var(--muted)", fontSize: 10 }} axisLine={false} tickLine={false} />
                <YAxis domain={[0, 100]} tick={{ fill: "var(--muted)", fontSize: 10 }} axisLine={false} tickLine={false} width={32} tickFormatter={(v) => `${v}%`} />
                <Tooltip
                  contentStyle={{ background: "var(--panel)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }}
                  formatter={(v: number) => [`${v}%`, "Utilization"]}
                />
                <Line type="monotone" dataKey="pct" stroke="#38bdf8" strokeWidth={2.5} dot={{ r: 3, fill: "#38bdf8" }} activeDot={{ r: 5 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
