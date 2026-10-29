import { useMemo } from "react";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from "recharts";
import type { ExecMetrics } from "../types";
import { buildAiPerformance, type AccuracyRing } from "../data/aiPerformance";

function mapeColor(mape: number): string {
  if (mape <= 10) return "#22c55e";
  if (mape <= 15) return "#f59e0b";
  return "#ef4444";
}

function AccuracyGauge({ ring }: { ring: AccuracyRing }) {
  const color = mapeColor(ring.mape);
  const data = [
    { name: "mape", value: ring.mape },
    { name: "rest", value: Math.max(0, 100 - ring.mape) },
  ];
  return (
    <div className="ai-gauge">
      <div className="ai-gauge-title">{ring.label}</div>
      <div className="ai-gauge-chart">
        <ResponsiveContainer width="100%" height={110}>
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              startAngle={90}
              endAngle={-270}
              innerRadius="72%"
              outerRadius="100%"
              stroke="none"
            >
              <Cell fill={color} />
              <Cell fill="var(--border-soft)" />
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        <div className="ai-gauge-center">
          <strong>{ring.mape}%</strong>
        </div>
      </div>
    </div>
  );
}

export default function AiPerformancePage({ metrics }: { metrics: ExecMetrics }) {
  const ap = useMemo(() => buildAiPerformance(metrics), [metrics]);
  const maxBenefit = Math.max(...ap.benefits.map((b) => b.valueThb));

  return (
    <div className="ai-page">
      <div className="ai-grid">
        {/* Prediction accuracy */}
        <div className="panel">
          <div className="panel-head">
            <h2>Prediction Accuracy (MAPE)</h2>
            <span className="hint">lower is better</span>
          </div>
          <div className="panel-body ai-gauges">
            {ap.accuracy.map((r) => (
              <AccuracyGauge key={r.label} ring={r} />
            ))}
          </div>
        </div>

        {/* Recommendation acceptance */}
        <div className="panel">
          <div className="panel-head">
            <h2>Recommendation Acceptance</h2>
          </div>
          <div className="panel-body ai-acceptance">
            <div className="ai-donut">
              <ResponsiveContainer width="100%" height={190}>
                <PieChart>
                  <Pie
                    data={ap.acceptance}
                    dataKey="value"
                    nameKey="name"
                    innerRadius="66%"
                    outerRadius="92%"
                    paddingAngle={2}
                    stroke="none"
                  >
                    {ap.acceptance.map((s) => (
                      <Cell key={s.name} fill={s.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ background: "var(--panel)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }}
                    formatter={(v: number, n: string) => [`${v}%`, n]}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="ai-donut-center">
                <strong>{ap.acceptanceRate}%</strong>
                <span>Accepted</span>
              </div>
            </div>
            <div className="ai-acceptance-legend">
              {ap.acceptance.map((s) => (
                <div className="ai-legend-row" key={s.name}>
                  <span className="status-dot" style={{ background: s.color }} />
                  <span className="ai-legend-name">{s.name}</span>
                  <span className="ai-legend-val">{s.value}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Forecast vs actual */}
        <div className="panel">
          <div className="panel-head">
            <h2>Forecast vs Actual (Overall)</h2>
            <span className="hint">daily net cash demand · THB M</span>
          </div>
          <div className="panel-body">
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={ap.forecast} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="var(--border-soft)" strokeDasharray="4 4" vertical={false} />
                <XAxis dataKey="day" tick={{ fill: "var(--muted)", fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: "var(--muted)", fontSize: 11 }} axisLine={false} tickLine={false} width={32} />
                <Tooltip
                  contentStyle={{ background: "var(--panel)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }}
                />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Line type="monotone" dataKey="actual" name="Actual" stroke="#1d4ed8" strokeWidth={2.5} dot={{ r: 3, fill: "#1d4ed8" }} activeDot={{ r: 5 }} />
                <Line type="monotone" dataKey="predicted" name="Predicted" stroke="#60a5fa" strokeWidth={2.5} strokeDasharray="6 4" dot={{ r: 3, fill: "#60a5fa" }} activeDot={{ r: 5 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Estimated annual benefit */}
        <div className="panel">
          <div className="panel-head">
            <h2>Estimated Annual Benefit</h2>
          </div>
          <div className="panel-body ai-benefits">
            {ap.benefits.map((b) => (
              <div className="ai-benefit-row" key={b.label}>
                <span className="ai-benefit-label">{b.label}</span>
                <div className="ai-benefit-track">
                  <div
                    className="ai-benefit-fill"
                    style={{ width: `${(b.valueThb / maxBenefit) * 100}%`, background: b.color }}
                  />
                </div>
                <span className="ai-benefit-val">THB {b.valueThb.toFixed(1)}M</span>
              </div>
            ))}
            <div className="ai-total-row">
              <span>TOTAL ESTIMATED BENEFIT</span>
              <strong>THB {ap.totalBenefit.toFixed(1)}M</strong>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
