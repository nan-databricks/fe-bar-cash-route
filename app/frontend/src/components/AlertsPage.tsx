import { useMemo, useState } from "react";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  LabelList,
} from "recharts";
import { AlertTriangle, ChevronRight } from "lucide-react";
import type { AppConfig, RouteExecution } from "../types";
import { buildAlerts, IMPACT_STYLE, STATUS_STYLE, type Alert } from "../data/alertsData";

function AlertKpi({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: "critical" | "high" | "medium" | "total";
}) {
  const colors = {
    critical: { border: "rgba(239,68,68,0.45)", bg: "var(--kpi-danger-bg)", icon: "#ef4444" },
    high: { border: "rgba(249,115,22,0.45)", bg: "var(--kpi-amber-bg)", icon: "#f97316" },
    medium: { border: "rgba(234,179,8,0.45)", bg: "var(--kpi-amber-bg)", icon: "#eab308" },
    total: { border: "var(--border)", bg: "linear-gradient(160deg, var(--panel) 0%, var(--panel-2) 100%)", icon: "#38bdf8" },
  };
  const c = colors[tone];
  return (
    <div className="alert-kpi" style={{ borderColor: c.border, background: c.bg }}>
      <AlertTriangle size={20} color={c.icon} />
      <div>
        <div className="alert-kpi-label">{label}</div>
        <div className="alert-kpi-value">{value}</div>
      </div>
    </div>
  );
}

function ImpactPill({ impact }: { impact: Alert["impact"] }) {
  const color = IMPACT_STYLE[impact];
  const label = impact === "Critical" ? "Critical" : impact;
  return (
    <span className="alert-pill" style={{ color, borderColor: `${color}55`, background: `${color}18` }}>
      {label}
    </span>
  );
}

function StatusPill({ status }: { status: Alert["status"] }) {
  const color = STATUS_STYLE[status];
  return (
    <span className="alert-pill" style={{ color, borderColor: `${color}55`, background: `${color}18` }}>
      {status}
    </span>
  );
}

export default function AlertsPage({
  config,
  execs,
}: {
  config: AppConfig;
  execs: RouteExecution[];
}) {
  const summary = useMemo(() => buildAlerts(config, execs), [config, execs]);
  const [showAll, setShowAll] = useState(false);
  const visible = showAll ? summary.alerts : summary.alerts.slice(0, 12);
  const total = summary.byType.reduce((s, d) => s + d.value, 0);

  return (
    <div className="alerts-page">
      <div className="alert-kpi-row">
        <AlertKpi label="Critical Alerts" value={summary.critical} tone="critical" />
        <AlertKpi label="High Alerts" value={summary.high} tone="high" />
        <AlertKpi label="Medium Alerts" value={summary.medium} tone="medium" />
        <AlertKpi label="Total Alerts" value={summary.total} tone="total" />
      </div>

      <div className="alerts-split">
        <div className="panel alerts-list-panel">
          <div className="panel-head">
            <h2>Alert List</h2>
            <span className="hint">{summary.total} open</span>
          </div>
          <div className="panel-body" style={{ padding: 0 }}>
            <table className="branch-table alerts-table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Type</th>
                  <th>Entity</th>
                  <th>Description</th>
                  <th>Impact</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((a) => (
                  <tr key={a.id}>
                    <td className="al-time">{a.time}</td>
                    <td>{a.type}</td>
                    <td style={{ fontWeight: 600 }}>{a.entity}</td>
                    <td className="al-desc">{a.description}</td>
                    <td>
                      <ImpactPill impact={a.impact} />
                    </td>
                    <td>
                      <StatusPill status={a.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!showAll && summary.alerts.length > 12 && (
              <button type="button" className="alerts-view-all" onClick={() => setShowAll(true)}>
                View All Alerts <ChevronRight size={14} />
              </button>
            )}
          </div>
        </div>

        <div className="alerts-charts">
          <div className="panel">
            <div className="panel-head">
              <h2>Alerts by Type</h2>
            </div>
            <div className="panel-body alerts-type-chart">
              <div className="alerts-type-legend">
                {summary.byType.map((d) => (
                  <div className="al-type-row" key={d.name}>
                    <span className="status-dot" style={{ background: d.color }} />
                    <span>{d.name}</span>
                    <span className="al-type-val">
                      {d.value} ({total ? Math.round((d.value / total) * 1000) / 10 : 0}%)
                    </span>
                  </div>
                ))}
              </div>
              <div className="alerts-donut-wrap">
                <ResponsiveContainer width="100%" height={200}>
                  <PieChart>
                    <Pie
                      data={summary.byType}
                      dataKey="value"
                      nameKey="name"
                      innerRadius="58%"
                      outerRadius="88%"
                      paddingAngle={2}
                      stroke="none"
                    >
                      {summary.byType.map((d) => (
                        <Cell key={d.name} fill={d.color} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{ background: "var(--panel)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          <div className="panel">
            <div className="panel-head">
              <h2>Alerts by Impact</h2>
              <span className="hint">Critical · High · Medium · Low</span>
            </div>
            <div className="panel-body">
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={summary.byImpact} layout="vertical" margin={{ top: 4, right: 36, left: 4, bottom: 0 }}>
                  <XAxis type="number" hide />
                  <YAxis
                    type="category"
                    dataKey="name"
                    tick={{ fill: "var(--muted)", fontSize: 12 }}
                    axisLine={false}
                    tickLine={false}
                    width={72}
                  />
                  <Tooltip
                    cursor={{ fill: "rgba(0,0,0,0.45)" }}
                    contentStyle={{ background: "var(--panel)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }}
                  />
                  <Bar dataKey="value" radius={[0, 6, 6, 0]} barSize={20}>
                    {summary.byImpact.map((d) => (
                      <Cell key={d.name} fill={d.color} />
                    ))}
                    <LabelList dataKey="value" position="right" fill="var(--text)" fontSize={12} fontWeight={700} />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
