import { useState } from "react";
import type { RouteExecution, StopStatus, StopType } from "../types";
import { thb } from "../data/format";

const STATUS_PILL: Record<string, string> = {
  "On Track": "#00A972",
  Delayed: "#FFAB00",
  "At Risk": "#C82D4C",
};

const STOP_STATUS_COLOR: Record<StopStatus, string> = {
  Completed: "#00A972",
  "In Progress": "#2272B4",
  Pending: "#8A9BA2",
};

const TYPE_COLOR: Record<StopType, string> = {
  Deliver: "#FFAB00",
  Pickup: "#2272B4",
  Mixed: "#8D4FD1",
  Start: "#00A972",
  Return: "#00A972",
};

const TYPE_LABEL: Record<StopType, string> = {
  Deliver: "Delivery",
  Pickup: "Pickup",
  Mixed: "Both (Del + Pick)",
  Start: "Start",
  Return: "Return",
};

import RoutePathMap from "./RoutePathMap";
import OverridesPanel from "./OverridesPanel";
import { PlanToggle } from "./PlanBar";
import type { PlanType } from "../data/api";

export default function RouteDetailPage({
  execs,
  initialRouteId,
  planType,
  onPlanChange,
  serviceDate,
}: {
  execs: RouteExecution[];
  initialRouteId?: string;
  planType: PlanType;
  onPlanChange: (p: PlanType) => void;
  serviceDate: string;
}) {
  const [routeId, setRouteId] = useState<string>(
    () => initialRouteId || execs[0]?.routeId || ""
  );
  const exec = execs.find((e) => e.routeId === routeId) ?? execs[0];
  if (!exec) return <div className="track-page">No routes available.</div>;

  const utilPct = Math.round((exec.cashOnBoard / exec.vehicleCapacity) * 100);

  return (
    <div className="track-page">
      <div className="detail-bar">
        <div className="detail-select">
          <label>Select Route</label>
          <select className="select-inline" value={routeId} onChange={(e) => setRouteId(e.target.value)}>
            {execs.map((e) => (
              <option key={e.routeId} value={e.routeId}>{e.routeId} · {e.label}</option>
            ))}
          </select>
        </div>
        <div className="detail-select">
          <label>Truck ID</label>
          <div className="detail-truck">{exec.truckId}</div>
        </div>
        <PlanToggle value={planType} onChange={onPlanChange} />
        <div className="detail-status" style={{ background: `${STATUS_PILL[exec.status]}22`, color: STATUS_PILL[exec.status], borderColor: `${STATUS_PILL[exec.status]}55` }}>
          ● {exec.status}
        </div>
      </div>

      <div className="detail-stats">
        <Stat label="Start Depot" value={exec.depot} wide />
        <Stat label="Total Stops" value={String(exec.totalStops)} />
        <Stat label="Completed" value={String(exec.completed)} tone="green" />
        <Stat label="Remaining" value={String(exec.remaining)} tone="amber" />
        <Stat label="Distance Left" value={`${exec.distanceLeftKm} km`} />
        <Stat label="ETA Return" value={exec.etaReturn} />
        {exec.citCostThb !== undefined && <Stat label="CIT Cost" value={thb(exec.citCostThb)} tone="amber" />}
      </div>

      <div className="track-split detail-split">
        <div className="panel">
          <div className="panel-head">
            <h2>{exec.routeId} · {exec.label}</h2>
            <span className="hint">{exec.truckId} · legend shows stop type · status · emergency</span>
          </div>
          <RoutePathMap exec={exec} />
        </div>

        <div className="panel">
          <div className="panel-head">
            <h2>Stop List</h2>
            <span className="hint">{exec.completed}/{exec.totalStops} completed</span>
          </div>
          <div className="panel-body" style={{ padding: 0, maxHeight: 470, overflowY: "auto" }}>
            <table className="branch-table stop-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Location</th>
                  <th>Type</th>
                  <th>Status</th>
                  <th className="num">ETA</th>
                  <th className="num">Amount</th>
                </tr>
              </thead>
              <tbody>
                {exec.stops.map((s) => (
                  <tr key={s.seq}>
                    <td style={{ color: "var(--muted)" }}>{s.type === "Start" ? "S" : s.type === "Return" ? "R" : s.seq}</td>
                    <td style={{ fontWeight: 600 }}>{s.location}</td>
                    <td><span style={{ color: TYPE_COLOR[s.type], fontWeight: 600 }}>{TYPE_LABEL[s.type]}</span></td>
                    <td>
                      <span style={{ display: "inline-flex", alignItems: "center", gap: 5, color: STOP_STATUS_COLOR[s.status] }}>
                        <span className="status-dot" style={{ background: STOP_STATUS_COLOR[s.status] }} />
                        {s.status}
                      </span>
                    </td>
                    <td className="num">{s.eta}</td>
                    <td className="num" style={{ color: s.amount > 0 ? "var(--t-amber)" : s.amount < 0 ? "#2272B4" : "var(--muted)" }}>
                      {s.amount === 0 ? "—" : `${s.amount > 0 ? "+" : "−"}${thb(Math.abs(s.amount))}`}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div className="detail-cash">
        <div className="cash-cap">
          <div className="cc-head">
            <span className="k-label">Vehicle Capacity (Cash)</span>
            <span>{thb(exec.cashOnBoard)} / {thb(exec.vehicleCapacity)} <b style={{ color: "#2272B4" }}>({utilPct}%)</b></span>
          </div>
          <div className="cc-bar"><div className="cc-fill" style={{ width: `${Math.min(100, utilPct)}%` }} /></div>
        </div>
        <Stat label="Cash On Board" value={`${thb(exec.cashOnBoard)}`} sub="Net secured" tone="sky" />
        <Stat label="Pickup Amount" value={thb(exec.pickupAmount)} sub="collected" tone="sky" />
        <Stat label="Delivery Amount" value={thb(exec.deliveryAmount)} sub="dispensed" tone="amber" />
      </div>

      <OverridesPanel exec={exec} serviceDate={serviceDate} />
    </div>
  );
}

function Stat({
  label,
  value,
  sub,
  tone,
  wide,
}: {
  label: string;
  value: string;
  sub?: string;
  tone?: "green" | "amber" | "sky";
  wide?: boolean;
}) {
  const color = tone === "green" ? "#00A972" : tone === "amber" ? "var(--t-amber)" : tone === "sky" ? "#2272B4" : undefined;
  return (
    <div className={`stat-box ${wide ? "wide" : ""}`}>
      <div className="k-label">{label}</div>
      <div className="k-value" style={{ color, fontSize: wide ? 15 : undefined }}>{value}</div>
      {sub && <div className="k-sub">{sub}</div>}
    </div>
  );
}
