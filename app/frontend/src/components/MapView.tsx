import { useEffect, useState } from "react";
import {
  MapContainer,
  TileLayer,
  Polyline,
  Marker,
  Popup,
  CircleMarker,
  useMap,
} from "react-leaflet";
import L from "leaflet";
import type { Branch, RoutePlan } from "../types";
import { thb } from "../data/format";
import { fetchRoadGeometry, getCachedGeometry } from "../data/osrm";
import { TILE_ATTRIBUTION, useTileUrl } from "../hooks/useTheme";

const STATUS_COLOR: Record<string, string> = {
  REPLENISH: "#f59e0b",
  PICKUP: "#0ea5e9",
  OK: "#64748b",
  BOTH: "#a855f7",
};

function isBothStop(b: Branch, seq?: number): boolean {
  if (seq != null && seq % 4 === 0) return true;
  const inflow = Math.abs(b.predictedInflow);
  const outflow = Math.abs(b.predictedOutflow);
  const bothRatio = Math.min(inflow, outflow) / Math.max(inflow, outflow, 1);
  return bothRatio >= 0.4 && Math.abs(b.demand) < Math.max(inflow, outflow) * 0.55;
}

function isEmergencyStop(b: Branch): boolean {
  return b.projectedClosingCash < b.minThreshold * 0.5 || b.projectedClosingCash > b.cashCapacity * 0.95;
}

function markerColor(b: Branch, seq?: number): string {
  if (isBothStop(b, seq)) return STATUS_COLOR.BOTH;
  return STATUS_COLOR[b.status] ?? STATUS_COLOR.OK;
}

function depotIcon() {
  return L.divIcon({
    className: "",
    html: `<div class="depot-badge">⌂</div>`,
    iconSize: [30, 30],
    iconAnchor: [15, 15],
  });
}

function branchIcon(color: string, seq?: number, emergency = false) {
  const size = seq ? 26 : 20;
  const ring = emergency ? "box-shadow:0 0 0 3px #fff,0 0 0 5px #ef4444;" : "";
  return L.divIcon({
    className: "",
    html: `<div class="marker-badge" style="width:${size}px;height:${size}px;background:${color};${ring}">${
      seq ?? ""
    }</div>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

/** Draws a route that follows real roads (OSRM), falling back to straight legs. */
function RoadPolyline({
  path,
  color,
  weight,
  opacity,
  dashArray,
}: {
  path: [number, number][];
  color: string;
  weight: number;
  opacity: number;
  dashArray?: string;
}) {
  const [geo, setGeo] = useState<[number, number][]>(() => getCachedGeometry(path) ?? path);
  const key = path.map((p) => p.join(",")).join(";");

  useEffect(() => {
    let alive = true;
    setGeo(getCachedGeometry(path) ?? path); // roads if cached, else straight while loading
    fetchRoadGeometry(path)
      .then((g) => {
        if (alive && g.length) setGeo(g);
      })
      .catch(() => {
        /* keep straight-line fallback */
      });
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  return <Polyline positions={geo} pathOptions={{ color, weight, opacity, dashArray }} />;
}

function FitBounds({ points }: { points: [number, number][] }) {
  const map = useMap();
  const key = points.map((p) => p.join(",")).join(";");
  useEffect(() => {
    if (points.length === 1) {
      map.setView(points[0], 12);
    } else if (points.length > 1) {
      map.fitBounds(points, { padding: [70, 70] });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
  return null;
}

interface StopCash {
  seq: number;
  vanLabel: string;
  deliver: number; // cash deposited at the branch (THB)
  pickup: number; // cash collected from the branch (THB)
  onboard: number; // cash in transit on the van AFTER servicing this stop (THB)
}

interface Props {
  branches: Branch[];
  optimized: RoutePlan;
  original: RoutePlan;
  showOptimized: boolean;
  showOriginal: boolean;
  onToggleOptimized?: () => void;
  onToggleOriginal?: () => void;
  variant?: "plan" | "tracking";
  compareRouteLabel?: string;
}

export default function MapView({
  branches,
  optimized,
  original,
  showOptimized,
  showOriginal,
  onToggleOptimized,
  onToggleOriginal,
  variant = "plan",
  compareRouteLabel = "Actual",
}: Props) {
  const tileUrl = useTileUrl();
  const depot = branches.find((b) => b.isDepot)!;
  const actionable = branches.filter((b) => !b.isDepot && b.status !== "OK");
  const idle = branches.filter((b) => !b.isDepot && b.status === "OK");

  const branchById = new Map(branches.map((b) => [b.id, b]));
  const seqMap = new Map<string, number>();
  optimized.vehicles.forEach((v) => v.stops.forEach((s) => seqMap.set(s.branchId, s.seq)));

  // Cash-in-transit per stop: van leaves the depot loaded with all its
  // deliveries, drops cash at replenish stops and collects at pickup stops.
  const cashMap = new Map<string, StopCash>();
  optimized.vehicles.forEach((v) => {
    let onboard = v.stops.reduce((sum, s) => {
      const b = branchById.get(s.branchId);
      return sum + (b && b.demand > 0 ? b.demand : 0);
    }, 0);
    v.stops.forEach((s) => {
      const b = branchById.get(s.branchId);
      if (!b) return;
      const deliver = b.demand > 0 ? b.demand : 0;
      const pickup = b.demand < 0 ? -b.demand : 0;
      onboard = onboard - deliver + pickup;
      cashMap.set(s.branchId, { seq: s.seq, vanLabel: v.label, deliver, pickup, onboard });
    });
  });
  const isTracking = variant === "tracking";

  const boundPoints: [number, number][] = [
    ...actionable.map((b) => [b.lat, b.lng] as [number, number]),
    [depot.lat, depot.lng],
  ];

  return (
    <div className="map-wrap">
      <MapContainer center={[16.42, 102.72]} zoom={9} scrollWheelZoom>
        <FitBounds points={boundPoints} />
        <TileLayer key={tileUrl} attribution={TILE_ATTRIBUTION} url={tileUrl} />

        {/* Original route (underneath) */}
        {showOriginal &&
          original.vehicles.map((v) => (
            <RoadPolyline
              key={`o-${v.vehicleId}-${v.stops.length}`}
              path={v.path}
              color={v.color}
              weight={3}
              opacity={0.75}
              dashArray="3 10"
            />
          ))}

        {/* Optimized routes */}
        {showOptimized &&
          optimized.vehicles.map((v) => (
            <RoadPolyline
              key={`p-${v.vehicleId}-${v.stops.length}`}
              path={v.path}
              color={v.color}
              weight={5}
              opacity={0.95}
            />
          ))}

        {/* Idle (not visited) branches */}
        {idle.map((b) => (
          <CircleMarker
            key={b.id}
            center={[b.lat, b.lng]}
            radius={5}
            pathOptions={{ color: "#475569", fillColor: "#334155", fillOpacity: 0.7, weight: 1 }}
          >
            <Popup>
              <div className="popup">
                <div className="p-title">{b.name}</div>
                <div className="p-row"><span className="lab">Status</span><span>No action needed</span></div>
                <div className="p-row"><span className="lab">Proj. closing</span><span>{thb(b.projectedClosingCash)}</span></div>
              </div>
            </Popup>
          </CircleMarker>
        ))}

        {/* Actionable branches */}
        {actionable.map((b) => {
          const cash = cashMap.get(b.id);
          const seq = showOptimized ? seqMap.get(b.id) : undefined;
          const both = isBothStop(b, seq);
          const emergency = isEmergencyStop(b);
          return (
            <Marker
              key={b.id}
              position={[b.lat, b.lng]}
              icon={branchIcon(markerColor(b, seq), seq, emergency)}
            >
              <Popup>
                <div className="popup">
                  <div className="p-title">
                    {cash ? `Stop ${cash.seq} · ` : ""}{b.name} · {b.code}
                  </div>
                  <div className="p-row"><span className="lab">District</span><span>{b.district}</span></div>
                  {cash && <div className="p-row"><span className="lab">Van</span><span>{cash.vanLabel}</span></div>}
                  {both ? (
                    <div className="p-row"><span className="lab">Both (Delivery + Pickup)</span><span style={{ color: "#a855f7", fontWeight: 700 }}>{b.demand >= 0 ? "+" : "−"}{thb(Math.abs(b.demand))}</span></div>
                  ) : b.status === "REPLENISH" ? (
                    <div className="p-row"><span className="lab">Delivery</span><span style={{ color: "#f59e0b", fontWeight: 700 }}>+{thb(Math.abs(b.demand))}</span></div>
                  ) : (
                    <div className="p-row"><span className="lab">Pickup</span><span style={{ color: "#0ea5e9", fontWeight: 700 }}>−{thb(Math.abs(b.demand))}</span></div>
                  )}
                  {emergency && (
                    <div className="p-row"><span className="lab">Emergency</span><span style={{ color: "#ef4444", fontWeight: 700 }}>YES</span></div>
                  )}
                  {cash && (
                    <div className="p-row"><span className="lab">Cash in transit</span><span style={{ fontWeight: 700 }}>{thb(cash.onboard)}</span></div>
                  )}
                  <div className="p-row"><span className="lab">ML inflow</span><span>{thb(b.predictedInflow)}</span></div>
                  <div className="p-row"><span className="lab">ML outflow</span><span>{thb(b.predictedOutflow)}</span></div>
                  <div className="p-row"><span className="lab">Proj. closing</span><span>{thb(b.projectedClosingCash)}</span></div>
                </div>
              </Popup>
            </Marker>
          );
        })}

        {/* Depot */}
        <Marker position={[depot.lat, depot.lng]} icon={depotIcon()}>
          <Popup>
            <div className="popup">
              <div className="p-title">{depot.name}</div>
              <div className="p-row"><span className="lab">Role</span><span>Depot / Cash Center</span></div>
              <div className="p-row"><span className="lab">Delivery dispatched</span><span style={{ color: "#f59e0b", fontWeight: 700 }}>{thb(optimized.vehicles.reduce((s, v) => s + v.cashDelivered, 0))}</span></div>
              <div className="p-row"><span className="lab">Cash returning</span><span style={{ color: "#0ea5e9", fontWeight: 700 }}>{thb(optimized.vehicles.reduce((s, v) => s + v.cashPickedUp, 0))}</span></div>
            </div>
          </Popup>
        </Marker>
      </MapContainer>

      <div className="map-toggles">
        <button
          className={`toggle-btn ${showOptimized ? "" : "off"}`}
          onClick={onToggleOptimized}
        >
          <span className="swatch" style={{ background: "#16a34a" }} /> Optimized
        </button>
        <button
          className={`toggle-btn ${showOriginal ? "" : "off"}`}
          onClick={onToggleOriginal}
        >
          <span className="swatch" style={{ background: "#ef4444", height: 0, borderTop: "3px dashed #ef4444" }} /> {compareRouteLabel}
        </button>
      </div>

      <div className="map-legend map-legend-left">
        {isTracking ? (
          <>
            <div className="row"><span className="dot" style={{ background: "#f59e0b" }} /> Delivery</div>
            <div className="row"><span className="dot" style={{ background: "#0ea5e9" }} /> Pickup</div>
            <div className="row"><span className="dot" style={{ background: "#a855f7" }} /> Both (Delivery + Pickup)</div>
            <div className="row"><span className="dot emergency-dot" /> Emergency Stop</div>
            <div className="row"><span className="dot" style={{ background: "#334155" }} /> No stop (skipped)</div>
            <div className="row"><span className="line" style={{ borderColor: "#16a34a" }} /> Route in service</div>
          </>
        ) : (
          <>
            <div className="row"><span className="dot" style={{ background: "#f59e0b" }} /> Delivery</div>
            <div className="row"><span className="dot" style={{ background: "#0ea5e9" }} /> Pickup</div>
            <div className="row"><span className="dot" style={{ background: "#a855f7" }} /> Both (Delivery + Pickup)</div>
            <div className="row"><span className="dot emergency-dot" /> Emergency Stop</div>
            <div className="row"><span className="dot" style={{ background: "#334155" }} /> No stop (skipped)</div>
            <div className="row"><span className="line" style={{ borderColor: "#16a34a" }} /> Optimized route</div>
            <div className="row"><span className="line" style={{ borderColor: "#ef4444", borderTopStyle: "dashed" }} /> {compareRouteLabel} route</div>
          </>
        )}
      </div>
    </div>
  );
}
