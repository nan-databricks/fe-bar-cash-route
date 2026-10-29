import { useMemo, useState } from "react";
import { Building2, Truck, PackageOpen, Repeat, MinusCircle, AlertTriangle } from "lucide-react";
import type { AppConfig, BranchTrack } from "../types";
import { generateBranchTracks, summarizeBranchTracks, HEALTH_COLOR } from "../data/tracking";
import { thb } from "../data/format";
import HealthMap, { type MapPoint } from "./HealthMap";
import TrendChart from "./TrendChart";
import { DenominationGap } from "./DenominationChart";
import ForecastPanel from "./ForecastPanel";

const ACTION_COLOR: Record<string, string> = {
  Deliver: "#f59e0b",
  Pickup: "#0ea5e9",
  "No Action": "#64748b",
  Both: "#a855f7",
};

const ALL_BRANCHES = "__all__";

export default function BranchTrackingPage({
  config,
  tracksOverride,
}: {
  config: AppConfig;
  tracksOverride?: BranchTrack[];
}) {
  const tracks = useMemo(
    () => tracksOverride ?? generateBranchTracks(config),
    [tracksOverride, config]
  );
  const summary = useMemo(() => summarizeBranchTracks(tracks), [tracks]);
  const [selectedCode, setSelectedCode] = useState<string>(() => tracks[0]?.code ?? "");
  const isAll = selectedCode === ALL_BRANCHES;
  const selected = tracks.find((t) => t.code === selectedCode) ?? tracks[0];

  const trendData = isAll ? summary.trendAll : selected?.trend ?? [];
  const trendLabel = isAll ? `All branches (${tracks.length})` : selected?.name;

  const points: MapPoint[] = tracks.map((t) => ({
    id: t.code,
    lat: t.lat,
    lng: t.lng,
    health: t.health,
    emphasize: t.emergency || t.code === selectedCode,
    title: `${t.name} · ${t.code}`,
    rows: [
      ["Actual Cash (d-1)", thb(t.currentCash)],
      ["Deposit", thb(t.deposit)],
      ["Withdraw", thb(t.withdraw)],
      ["Predicted Cash (d)", thb(Math.max(0, t.currentCash + t.forecastNet))],
      ["Action", t.action],
      ...(t.emergency ? ([["Emergency", "YES"]] as [string, string][]) : []),
    ],
  }));

  return (
    <div className="track-page">
      <div className="page-toolbar">
        <span className="pt-title">Branch Tracking · {tracks.length} branches</span>
      </div>

      <div className="kpi-grid track-kpis six">
        <TrackKpi icon={<Building2 size={18} color="#38bdf8" />} label="Total branches" value={String(summary.total)} delta="2.1%" dir="up" good />
        <TrackKpi icon={<Truck size={18} color="#f59e0b" />} label="Delivery" value={String(summary.delivery)} delta="8.3%" dir="up" tone="amber" />
        <TrackKpi icon={<PackageOpen size={18} color="#0ea5e9" />} label="Pickup" value={String(summary.pickup)} delta="5.6%" dir="up" tone="sky" />
        <TrackKpi icon={<Repeat size={18} color="#a855f7" />} label="Both (Del + Pick)" value={String(summary.both)} delta="0%" dir="up" />
        <TrackKpi icon={<MinusCircle size={18} color="#64748b" />} label="No action" value={String(summary.noAction)} delta="12%" dir="down" good />
        <TrackKpi icon={<AlertTriangle size={18} color="#ef4444" />} label="Emergency" value={String(summary.emergency)} delta="14.3%" dir="down" good tone="red" />
      </div>

      <div className="track-split">
        <div className="panel">
          <div className="panel-head">
            <h2>Branch Health Map</h2>
            <span className="hint">{tracks.length} branches · emphasized = emergency</span>
          </div>
          <HealthMap points={points} showEmergencyLegend />
        </div>

        <div className="panel">
          <div className="panel-head">
            <h2>Branch Summary</h2>
            <span className="hint">actual cash · deposit / withdraw · predicted cash</span>
          </div>
          <div className="panel-body" style={{ padding: 0, maxHeight: 430, overflowY: "auto" }}>
            <table className="branch-table">
              <thead>
                <tr>
                  <th>Branch</th>
                  <th className="num">Actual Cash (d-1)</th>
                  <th className="num">Deposit</th>
                  <th className="num">Withdraw</th>
                  <th className="num">Predicted Cash (d)</th>
                  <th>Action</th>
                  <th className="num">Conf.</th>
                </tr>
              </thead>
              <tbody>
                {tracks.map((t) => (
                  <tr
                    key={t.code}
                    onClick={() => setSelectedCode(t.code)}
                    style={{ cursor: "pointer", background: t.code === selectedCode ? "rgba(56,189,248,0.08)" : undefined }}
                  >
                    <td>
                      <div style={{ fontWeight: 600, display: "flex", alignItems: "center", gap: 6 }}>
                        <span className="status-dot" style={{ background: HEALTH_COLOR[t.health] }} />
                        {t.name}
                        {t.emergency && <AlertTriangle size={12} color="#ef4444" />}
                      </div>
                      <div style={{ color: "var(--muted)", fontSize: 10 }}>
                        {t.code} · {t.district}
                      </div>
                    </td>
                    <td className="num">{thb(t.currentCash)}</td>
                    <td className="num" style={{ color: "#22c55e" }}>
                      {thb(t.deposit)}
                    </td>
                    <td className="num" style={{ color: "#f59e0b" }}>
                      {thb(t.withdraw)}
                    </td>
                    <td className="num">{thb(Math.max(0, t.currentCash + t.forecastNet))}</td>
                    <td>
                      <span style={{ color: ACTION_COLOR[t.action], fontWeight: 600 }}>{t.action}</span>
                    </td>
                    <td className="num">{t.confidence}%</td>
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
            <h2>Cash Position Analysis (Actual vs Predicted) · {trendLabel}</h2>
            <select className="select-inline" value={selectedCode} onChange={(e) => setSelectedCode(e.target.value)}>
              <option value={ALL_BRANCHES}>All branches ({tracks.length})</option>
              {tracks.map((t) => (
                <option key={t.code} value={t.code}>
                  {t.name}
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
            <h2>Denomination Gap (Net)</h2>
            <span className="hint">surplus (+) / shortfall (−) by note</span>
          </div>
          <div className="panel-body">
            <DenominationGap data={summary.denominationGap} height={220} />
          </div>
        </div>
      </div>

      <ForecastPanel
        nodeId={isAll ? undefined : selected?.code}
        title={isAll ? undefined : `${selected?.code} · ${selected?.name}`}
      />
    </div>
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
  tone?: "red" | "amber" | "green" | "sky";
}) {
  const signed =
    delta.startsWith("+") || delta.startsWith("−") || delta.startsWith("-")
      ? delta
      : `${dir === "up" ? "+" : "−"}${delta}`;
  return (
    <div
      className={`kpi ${
        tone === "green"
          ? "hero"
          : tone === "red"
            ? "danger-kpi"
            : tone === "amber"
              ? "amber-kpi"
              : tone === "sky"
                ? "cash"
                : ""
      }`}
    >
      <span className="icon">{icon}</span>
      <div className="k-label">{label}</div>
      <div className="k-value">{value}</div>
      <div className="k-delta">
        <span className={good ? "up" : "down"}>
          {dir === "up" ? "▲" : "▼"} {signed}
        </span>
        <span className="kd-label">vs last week</span>
      </div>
    </div>
  );
}
