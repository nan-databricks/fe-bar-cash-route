import ForecastPanel from "./ForecastPanel";
import { useMemo, useState } from "react";
import {
  Cpu,
  TrendingDown,
  TrendingUp,
  ShieldCheck,
  AlertTriangle,
  ChevronUp,
  ChevronDown,
  ChevronsUpDown,
} from "lucide-react";
import { summarizeMachines, HEALTH_COLOR, machineActionLabel, deriveMachine } from "../data/tracking";
import { loadMachines } from "../data/machineStore";
import type { Machine, RiskLevel, DayFlow } from "../types";
import { thb } from "../data/format";
import HealthMap, { type MapPoint } from "./HealthMap";
import TrendChart from "./TrendChart";
import { DenominationDonut } from "./DenominationChart";

const ALL_MACHINES = "__all__";

const RISK_ORDER: Record<RiskLevel, number> = { "Very High": 0, High: 1, Medium: 2, Low: 3 };

type SortKey = "machine" | "current" | "eod" | "flow" | "action" | "risk" | "conf";
type SortDir = "asc" | "desc";

const RISK_COLOR: Record<RiskLevel, string> = {
  "Very High": "#ef4444",
  High: "#f97316",
  Medium: "#eab308",
  Low: "#22c55e",
};

const ACTION_COLOR: Record<string, string> = {
  "Swap (Near Empty)": "#f59e0b",
  "Swap (Near Full)": "#0ea5e9",
  "No Action": "#64748b",
};

export default function MachineTrackingPage({
  machinesOverride,
}: {
  machinesOverride?: Machine[];
}) {
  const machines = useMemo(
    () => machinesOverride ?? loadMachines().map(deriveMachine),
    [machinesOverride]
  );
  const summary = useMemo(() => summarizeMachines(machines), [machines]);
  const [selectedId, setSelectedId] = useState<string>(
    () => machines.find((m) => m.action !== "No Action")?.id ?? machines[0]?.id ?? ""
  );
  const [sortKey, setSortKey] = useState<SortKey>("risk");
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  const isAll = selectedId === ALL_MACHINES;
  const selected = machines.find((m) => m.id === selectedId) ?? machines[0];

  const allTrend = useMemo<DayFlow[]>(() => {
    if (!machines.length) return [];
    return machines[0].trend.map((_, i) => {
      const deposit = machines.reduce((s, m) => s + (m.trend[i]?.deposit ?? 0), 0);
      const withdraw = machines.reduce((s, m) => s + (m.trend[i]?.withdraw ?? 0), 0);
      return { day: machines[0].trend[i].day, deposit, withdraw, net: deposit - withdraw };
    });
  }, [machines]);

  const trendData = isAll ? allTrend : selected?.trend ?? [];
  const trendLabel = isAll ? `All machines (${machines.length})` : selected?.id;

  const points: MapPoint[] = machines.map((m) => ({
    id: m.id,
    lat: m.lat,
    lng: m.lng,
    health: m.health,
    title: `${m.id} · ${m.location}`,
    emphasize: m.emergency || m.id === selectedId,
    rows: [
      ["Actual Cash (d-1)", thb(m.currentCash)],
      ["Predicted Cash (d)", thb(m.predictedEod)],
      [
        "Deposit / Withdrawal (d)",
        `+${thb(m.depositToday, false)} / −${thb(m.withdrawToday, false)}`,
      ],
      ["Action", machineActionLabel(m.action)],
      ["Risk", m.riskLevel],
      ...(m.emergency ? ([["Emergency", "YES"]] as [string, string][]) : []),
    ],
  }));

  const toggleSort = (col: SortKey) => {
    if (sortKey === col) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else {
      setSortKey(col);
      setSortDir(col === "risk" || col === "action" ? "asc" : "desc");
    }
  };

  const ranked = useMemo(() => {
    const val = (m: Machine): string | number => {
      switch (sortKey) {
        case "machine":
          return m.id;
        case "current":
          return m.currentCash;
        case "eod":
          return m.predictedEod;
        case "flow":
          return m.depositToday - m.withdrawToday;
        case "action":
          return machineActionLabel(m.action);
        case "risk":
          return RISK_ORDER[m.riskLevel];
        case "conf":
          return m.confidence;
      }
    };
    const dir = sortDir === "asc" ? 1 : -1;
    return [...machines].sort((a, b) => {
      const av = val(a);
      const bv = val(b);
      if (typeof av === "number" && typeof bv === "number") return (av - bv) * dir;
      return String(av).localeCompare(String(bv)) * dir;
    });
  }, [machines, sortKey, sortDir]);

  return (
    <div className="track-page">
      <div className="page-toolbar">
        <span className="pt-title">Machine Tracking · {machines.length} machines</span>
      </div>

      <div className="kpi-grid track-kpis five">
        <TrackKpi icon={<Cpu size={20} color="#38bdf8" />} label="Total machines" value={summary.total.toLocaleString()} delta="4.3%" dir="up" good />
        <TrackKpi icon={<TrendingDown size={20} color="#ef4444" />} label="Cash-out risk" value={String(summary.cashOutRisk)} delta="12.5%" dir="up" tone="red" />
        <TrackKpi icon={<TrendingUp size={20} color="#f59e0b" />} label="Overflow risk" value={String(summary.overflowRisk)} delta="6.7%" dir="down" good tone="amber" />
        <TrackKpi icon={<ShieldCheck size={20} color="#22c55e" />} label="Healthy" value={summary.healthy.toLocaleString()} delta="8.2%" dir="up" good tone="green" />
        <TrackKpi icon={<AlertTriangle size={20} color="#ef4444" />} label="Emergency" value={String(summary.emergency)} delta="14.3%" dir="down" good tone="red" />
      </div>

      <div className="track-split">
        <div className="panel">
          <div className="panel-head">
            <h2>Machine Health Map</h2>
            <span className="hint">{machines.length} machines · emphasized = emergency</span>
          </div>
          <HealthMap points={points} showEmergencyLegend />
        </div>

        <div className="panel">
          <div className="panel-head">
            <h2>Machine Summary</h2>
            <span className="hint">by predicted risk</span>
          </div>
          <div className="panel-body" style={{ padding: 0, maxHeight: 430, overflowY: "auto" }}>
            <table className="branch-table">
              <thead>
                <tr>
                  <SortTh label="Machine" col="machine" sortKey={sortKey} sortDir={sortDir} onSort={toggleSort} />
                  <SortTh label="Actual Cash (d-1)" col="current" num sortKey={sortKey} sortDir={sortDir} onSort={toggleSort} />
                  <SortTh label="Predicted Cash (d)" col="eod" num sortKey={sortKey} sortDir={sortDir} onSort={toggleSort} />
                  <SortTh label="Deposit / Withdrawal Amount (d)" col="flow" num sortKey={sortKey} sortDir={sortDir} onSort={toggleSort} />
                  <SortTh label="Action" col="action" sortKey={sortKey} sortDir={sortDir} onSort={toggleSort} />
                  <SortTh label="Risk" col="risk" sortKey={sortKey} sortDir={sortDir} onSort={toggleSort} />
                  <SortTh label="Conf." col="conf" num sortKey={sortKey} sortDir={sortDir} onSort={toggleSort} />
                </tr>
              </thead>
              <tbody>
                {ranked.map((m) => (
                  <tr
                    key={m.id}
                    onClick={() => setSelectedId(m.id)}
                    style={{ cursor: "pointer", background: m.id === selectedId ? "rgba(56,189,248,0.08)" : undefined }}
                  >
                    <td>
                      <div style={{ fontWeight: 600, display: "flex", alignItems: "center", gap: 6 }}>
                        <span className="status-dot" style={{ background: HEALTH_COLOR[m.health] }} />
                        {m.id}
                        {m.emergency && <AlertTriangle size={12} color="#ef4444" />}
                      </div>
                      <div style={{ color: "var(--muted)", fontSize: 10 }}>{m.location}</div>
                    </td>
                    <td className="num">{thb(m.currentCash)}</td>
                    <td className="num">{thb(m.predictedEod)}</td>
                    <td className="num">
                      <span style={{ color: "#22c55e" }}>+{thb(m.depositToday, false)}</span>
                      <span style={{ color: "var(--muted)", margin: "0 4px" }}>/</span>
                      <span style={{ color: "#ef4444" }}>−{thb(m.withdrawToday, false)}</span>
                    </td>
                    <td>
                      <span style={{ color: ACTION_COLOR[machineActionLabel(m.action)], fontWeight: 600 }}>
                        {machineActionLabel(m.action)}
                      </span>
                    </td>
                    <td>
                      <span style={{ color: RISK_COLOR[m.riskLevel], fontWeight: 600, fontSize: 11 }}>
                        {m.riskLevel}
                      </span>
                    </td>
                    <td className="num">{m.confidence}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div className="track-split">
        <div className="panel">
          <div className="panel-head">
            <h2>Daily Trend · {trendLabel}</h2>
            <select className="select-inline" value={selectedId} onChange={(e) => setSelectedId(e.target.value)}>
              <option value={ALL_MACHINES}>All machines ({machines.length})</option>
              {machines.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.id} · {m.location}
                </option>
              ))}
            </select>
          </div>
          <div className="panel-body">
            {trendData.length > 0 && <TrendChart data={trendData} height={220} splitActualPredicted />}
            <div className="trend-caption">Solid = Actual · Dashed = Predicted (Deposit · Withdrawal · Net)</div>
          </div>
        </div>

        <div className="panel">
          <div className="panel-head">
            <h2>Predicted Denomination Mix (d)</h2>
            <span className="hint">{selected?.id ?? "—"}</span>
          </div>
          <div className="panel-body">
            {selected && <DenominationDonut data={selected.denomination} />}
          </div>
        </div>
      </div>

      <ForecastPanel
        nodeId={isAll ? undefined : selected?.id}
        title={isAll ? undefined : `${selected?.id} · ${selected?.location}`}
      />
    </div>
  );
}

function SortTh({
  label,
  col,
  num,
  sortKey,
  sortDir,
  onSort,
}: {
  label: string;
  col: SortKey;
  num?: boolean;
  sortKey: SortKey;
  sortDir: SortDir;
  onSort: (col: SortKey) => void;
}) {
  const active = sortKey === col;
  return (
    <th className={num ? "num" : undefined} style={{ cursor: "pointer", userSelect: "none" }} onClick={() => onSort(col)}>
      <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
        {label}
        {active ? sortDir === "asc" ? <ChevronUp size={12} /> : <ChevronDown size={12} /> : <ChevronsUpDown size={12} opacity={0.35} />}
      </span>
    </th>
  );
}

function TrackKpi({
  icon,
  label,
  value,
  delta,
  dir,
  good,
  tone,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  delta: string;
  dir: "up" | "down";
  good?: boolean;
  tone?: "red" | "amber" | "green";
}) {
  return (
    <div className={`track-kpi ${tone ?? ""}`}>
      <div className="tk-icon">{icon}</div>
      <div className="tk-label">{label}</div>
      <div className="tk-value">{value}</div>
      <div className={`tk-delta ${good ? "good" : "bad"}`}>
        {dir === "up" ? "▲" : "▼"} {delta}
      </div>
    </div>
  );
}
