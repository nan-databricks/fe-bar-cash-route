import { useEffect, useState } from "react";
import { MapContainer, TileLayer, Polyline, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import type { RouteExecution } from "../types";
import { thb } from "../data/format";
import { fetchRoadGeometry, getCachedGeometry } from "../data/osrm";
import { TILE_ATTRIBUTION, useTileUrl } from "../hooks/useTheme";

const TYPE_COLOR: Record<string, string> = {
  Deliver: "#f59e0b",
  Pickup: "#0ea5e9",
  Mixed: "#a855f7",
  Start: "#22c55e",
  Return: "#22c55e",
};

const STATUS_RING: Record<string, string> = {
  Completed: "#22c55e",
  "In Progress": "#38bdf8",
  Pending: "#64748b",
};

function depotIcon() {
  return L.divIcon({ className: "", html: `<div class="depot-badge">⌂</div>`, iconSize: [28, 28], iconAnchor: [14, 14] });
}

function stopIcon(color: string, ring: string, seq: number) {
  return L.divIcon({
    className: "",
    html: `<div class="marker-badge" style="width:26px;height:26px;background:${color};box-shadow:0 0 0 3px ${ring}">${seq}</div>`,
    iconSize: [26, 26],
    iconAnchor: [13, 13],
  });
}

function RoadPolyline({ path, color }: { path: [number, number][]; color: string }) {
  const [geo, setGeo] = useState<[number, number][]>(() => getCachedGeometry(path) ?? path);
  const key = path.map((p) => p.join(",")).join(";");
  useEffect(() => {
    let alive = true;
    setGeo(getCachedGeometry(path) ?? path);
    fetchRoadGeometry(path).then((g) => alive && g.length && setGeo(g)).catch(() => {});
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
  return <Polyline positions={geo} pathOptions={{ color, weight: 5, opacity: 0.95 }} />;
}

function FitBounds({ points }: { points: [number, number][] }) {
  const map = useMap();
  const key = points.map((p) => p.join(",")).join(";");
  useEffect(() => {
    if (points.length > 1) map.fitBounds(points, { padding: [50, 50] });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
  return null;
}

export default function RoutePathMap({ exec }: { exec: RouteExecution }) {
  const tileUrl = useTileUrl();
  const service = exec.stops.filter((s) => s.type !== "Start" && s.type !== "Return");
  const points: [number, number][] = exec.path;
  return (
    <div className="health-map">
      <MapContainer center={[exec.depotLat, exec.depotLng]} zoom={11} scrollWheelZoom>
        <FitBounds points={points} />
        <TileLayer key={tileUrl} attribution={TILE_ATTRIBUTION} url={tileUrl} />
        <RoadPolyline path={exec.path} color={exec.color} />
        {service.map((s) => (
          <Marker key={s.seq} position={[s.lat, s.lng]} icon={stopIcon(TYPE_COLOR[s.type], STATUS_RING[s.status], s.seq)}>
            <Popup>
              <div className="popup">
                <div className="p-title">{s.seq}. {s.location}</div>
                <div className="p-row"><span className="lab">Type</span><span>{s.type === "Deliver" ? "Delivery" : s.type === "Mixed" ? "Both (Delivery + Pickup)" : s.type}</span></div>
                <div className="p-row"><span className="lab">Status</span><span>{s.status}</span></div>
                <div className="p-row"><span className="lab">ETA</span><span>{s.eta}</span></div>
                <div className="p-row"><span className="lab">Amount</span><span>{s.amount >= 0 ? "+" : "−"}{thb(Math.abs(s.amount))}</span></div>
              </div>
            </Popup>
          </Marker>
        ))}
        <Marker position={[exec.depotLat, exec.depotLng]} icon={depotIcon()}>
          <Popup>
            <div className="popup">
              <div className="p-title">{exec.depot}</div>
              <div className="p-row"><span className="lab">Role</span><span>Depot / Cash Center</span></div>
            </div>
          </Popup>
        </Marker>
      </MapContainer>
      <div className="map-legend map-legend-left route-detail-legend">
        <div className="legend-group-label">Stop type</div>
        <div className="row"><span className="dot" style={{ background: TYPE_COLOR.Deliver }} /> Delivery</div>
        <div className="row"><span className="dot" style={{ background: TYPE_COLOR.Pickup }} /> Pickup</div>
        <div className="row"><span className="dot" style={{ background: TYPE_COLOR.Mixed }} /> Both (Delivery + Pickup)</div>
        <div className="row"><span className="dot emergency-dot" /> Emergency Stop</div>
        <div className="legend-group-label">Stop status</div>
        <div className="row"><span className="dot" style={{ background: STATUS_RING.Completed }} /> Completed</div>
        <div className="row"><span className="dot" style={{ background: STATUS_RING["In Progress"] }} /> In Progress</div>
        <div className="row"><span className="dot" style={{ background: STATUS_RING.Pending }} /> Pending</div>
        <div className="legend-group-label">Route</div>
        <div className="row"><span className="line" style={{ borderColor: exec.color }} /> Route path</div>
        <div className="row"><span className="dot depot-legend-dot" /> Depot</div>
      </div>
    </div>
  );
}
