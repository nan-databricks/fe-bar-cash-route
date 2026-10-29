import { useEffect, useState } from "react";
import { Area, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { RefreshCw } from "lucide-react";
import { postForecast, type ForecastResponse } from "../data/api";
import { thb } from "../data/format";

const SOURCE_LABEL: Record<string, string> = {
  serving_endpoint: "Model Serving · live",
  forecast_table: "gold_demand_forecast (batch)",
  mock: "mock fixture",
};

/** "Re-forecast" a node through POST /api/forecast (snb-cash-forecast endpoint) and chart 7 days. */
export default function ForecastPanel({ nodeId, title }: { nodeId?: string; title?: string }) {
  const [data, setData] = useState<ForecastResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    setData(null);
    setError("");
  }, [nodeId]);

  const run = async () => {
    if (!nodeId) return;
    setLoading(true);
    setError("");
    try {
      setData(await postForecast(nodeId));
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  const chart = data
    ? [
        ...data.history.slice(-7).map((h) => ({ day: h.date.slice(5), actual: h.net_outflow_thb })),
        ...data.forecast.map((f) => ({
          day: f.forecast_date.slice(5),
          forecast: f.pred_net_outflow_thb,
          band: [f.pred_net_outflow_thb, f.pred_p80_thb] as [number, number],
        })),
      ]
    : [];
  const total7 = data ? data.forecast.reduce((s, f) => s + f.pred_net_outflow_thb, 0) : 0;

  return (
    <div className="panel forecast-panel">
      <div className="panel-head">
        <h2>7-day Cash Demand Forecast · {title ?? nodeId ?? "select a node"}</h2>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          {data && (
            <span className={`source-chip ${data.source === "serving_endpoint" ? "live" : ""}`}>
              {SOURCE_LABEL[data.source] ?? data.source}
            </span>
          )}
          <button className="btn sm primary" disabled={!nodeId || loading} onClick={run}>
            <RefreshCw size={13} className={loading ? "spin" : ""} /> {loading ? "Scoring…" : "Re-forecast"}
          </button>
        </div>
      </div>
      <div className="panel-body">
        {error && <div className="error-text">{error}</div>}
        {!data && !error && (
          <div className="empty-hint">
            Click <b>Re-forecast</b> to score the next 7 days for <b>{nodeId ?? "—"}</b> on the{" "}
            <code>snb-cash-forecast</code> Model Serving endpoint (features from <code>gold_demand_features</code>).
          </div>
        )}
        {data && (
          <>
            <ResponsiveContainer width="100%" height={230}>
              <ComposedChart data={chart} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
                <XAxis dataKey="day" tick={{ fontSize: 11, fill: "var(--muted)" }} />
                <YAxis tickFormatter={(v) => thb(Number(v))} tick={{ fontSize: 11, fill: "var(--muted)" }} width={64} />
                <Tooltip
                  formatter={(v: unknown) => (Array.isArray(v) ? `${thb(v[0])} – ${thb(v[1])}` : thb(Number(v)))}
                  contentStyle={{ background: "var(--popup-bg)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }}
                />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Area dataKey="band" name="P50–P80 band" fill="#f2a900" fillOpacity={0.18} stroke="none" />
                <Line dataKey="actual" name="Actual net outflow" stroke="#38bdf8" strokeWidth={2} dot={{ r: 2 }} />
                <Line dataKey="forecast" name="Forecast (P50)" stroke="#f2a900" strokeWidth={2} strokeDasharray="5 4" dot={{ r: 3 }} />
              </ComposedChart>
            </ResponsiveContainer>
            <div className="forecast-foot">
              <span>7-day net outflow: <b>{thb(total7)}</b></span>
              <span>Day-1 P80: <b>{thb(data.forecast[0]?.pred_p80_thb ?? 0)}</b></span>
              <span>Features: {data.features_source === "unity_catalog" ? "UC gold_demand_features" : "mock"}</span>
              <span>Endpoint: <code>{data.endpoint}</code></span>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
