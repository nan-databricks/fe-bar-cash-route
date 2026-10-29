import { useState } from "react";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  ReferenceLine,
  LabelList,
  Sector,
} from "recharts";
import type { Denomination } from "../types";

const DENOM_COLORS = ["#38bdf8", "#22c55e", "#f59e0b", "#a855f7"];

function toRows(d: Denomination) {
  return [
    { name: "฿1000", value: d.b1000 },
    { name: "฿500", value: d.b500 },
    { name: "฿100", value: d.b100 },
    { name: "฿50", value: d.b50 },
  ];
}

/** Hover highlight: dark/black band on the active slice. */
function ActiveDonutSlice({
  cx,
  cy,
  innerRadius,
  outerRadius,
  startAngle,
  endAngle,
}: {
  cx?: number;
  cy?: number;
  innerRadius?: number;
  outerRadius?: number;
  startAngle?: number;
  endAngle?: number;
  fill?: string;
}) {
  return (
    <Sector
      cx={cx}
      cy={cy}
      innerRadius={innerRadius}
      outerRadius={(outerRadius ?? 0) + 6}
      startAngle={startAngle}
      endAngle={endAngle}
      fill="#0a0a0a"
      stroke="#e2e8f0"
      strokeWidth={1.5}
    />
  );
}

function DenomLegend({
  rows,
  activeIndex,
  onHover,
}: {
  rows: { name: string; value: number }[];
  activeIndex: number | null;
  onHover: (i: number | null) => void;
}) {
  return (
    <ul className="denom-legend">
      {rows.map((r, i) => (
        <li
          key={r.name}
          className={activeIndex === i ? "active" : ""}
          onMouseEnter={() => onHover(i)}
          onMouseLeave={() => onHover(null)}
        >
          <span className="denom-swatch" style={{ background: DENOM_COLORS[i] }} />
          <span className="denom-name">{r.name}</span>
          <span className="denom-pct">{r.value}%</span>
        </li>
      ))}
    </ul>
  );
}

export function DenominationDonut({ data, height = 180 }: { data: Denomination; height?: number }) {
  const rows = toRows(data);
  const [activeIndex, setActiveIndex] = useState<number | null>(null);
  const chartH = Math.max(120, height - 52);

  return (
    <div className="denom-donut-wrap">
      <ResponsiveContainer width="100%" height={chartH}>
        <PieChart>
          <Pie
            data={rows}
            dataKey="value"
            nameKey="name"
            innerRadius="52%"
            outerRadius="80%"
            paddingAngle={2}
            stroke="none"
            activeIndex={activeIndex ?? undefined}
            activeShape={ActiveDonutSlice}
            onMouseEnter={(_, index) => setActiveIndex(index)}
            onMouseLeave={() => setActiveIndex(null)}
          >
            {rows.map((_, i) => (
              <Cell key={i} fill={DENOM_COLORS[i]} />
            ))}
            <LabelList
              dataKey="value"
              position="outside"
              fill="var(--muted)"
              fontSize={10}
              formatter={(v: number) => `${v}%`}
            />
          </Pie>
          <Tooltip
            contentStyle={{
              background: "var(--popup-bg, var(--panel))",
              border: "1px solid var(--border)",
              borderRadius: 8,
              fontSize: 12,
              color: "var(--text)",
              boxShadow: "0 8px 24px rgba(0, 0, 0, 0.2)",
            }}
            labelStyle={{ color: "var(--text)" }}
            itemStyle={{ color: "var(--text)" }}
            formatter={(v: number, n: string) => [`${v}%`, n]}
          />
        </PieChart>
      </ResponsiveContainer>
      <DenomLegend rows={rows} activeIndex={activeIndex} onHover={setActiveIndex} />
    </div>
  );
}

function gapAmount(v: number): string {
  const sign = v < 0 ? "−" : "+";
  const abs = Math.abs(v);
  if (abs >= 1_000_000) return `${sign}฿${(abs / 1_000_000).toFixed(1)}M`;
  return `${sign}฿${Math.round(abs / 1000)}K`;
}

/** Label sits just outside the bar end, flipping side with the sign. */
function GapLabel(props: { x?: number; y?: number; width?: number; height?: number; value?: number }) {
  const { x = 0, y = 0, width = 0, height = 0, value = 0 } = props;
  const negative = value < 0;
  // Recharts may report width as negative for left-growing bars.
  const left = Math.min(x, x + width);
  const right = Math.max(x, x + width);
  const tx = negative ? left - 8 : right + 8;
  return (
    <text
      x={tx}
      y={y + height / 2}
      dy={4}
      textAnchor={negative ? "end" : "start"}
      fontSize={10}
      fontWeight={600}
      fill={negative ? "#ef4444" : "#22c55e"}
    >
      {gapAmount(value)}
    </text>
  );
}

function GapTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ value?: number }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  const value = Number(payload[0].value ?? 0);
  return (
    <div className="gap-tooltip">
      <div className="gap-tooltip-label">{label}</div>
      <div className="gap-tooltip-value">
        Gap: {value < 0 ? "−" : "+"}฿{Math.abs(value).toLocaleString()}
      </div>
    </div>
  );
}

export function DenominationGap({ data, height = 180 }: { data: Denomination; height?: number }) {
  const rows = toRows(data).map((r) => ({ ...r, fill: r.value >= 0 ? "#22c55e" : "#ef4444" }));
  // Symmetric domain with headroom keeps 0 centred and leaves space for labels.
  const bound = Math.max(...rows.map((r) => Math.abs(r.value)), 1) * 1.35;

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={rows} layout="vertical" margin={{ top: 6, right: 12, left: 4, bottom: 2 }}>
        <XAxis type="number" domain={[-bound, bound]} hide />
        <YAxis
          type="category"
          dataKey="name"
          tick={{ fill: "var(--muted)", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          width={52}
        />
        <Tooltip
          cursor={false}
          content={<GapTooltip />}
        />
        <ReferenceLine x={0} stroke="var(--border)" />
        <Bar
          dataKey="value"
          radius={[4, 4, 4, 4]}
          barSize={18}
          activeBar={false}
        >
          {rows.map((r, i) => (
            <Cell key={i} fill={r.fill} />
          ))}
          <LabelList dataKey="value" content={<GapLabel />} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
