import { useEffect } from "react";
import { CircleMarker, MapContainer, Marker, Polyline, Popup, TileLayer, useMap } from "react-leaflet";
import L from "leaflet";
import type { RouteExecution } from "../types";
import { thb } from "../data/format";
import { TILE_ATTRIBUTION, useTileUrl } from "../hooks/useTheme";

function depotIcon() {
  return L.divIcon({ className: "", html: `<div class="depot-badge">⌂</div>`, iconSize: [28, 28], iconAnchor: [14, 14] });
}

function FitBounds({ points }: { points: [number, number][] }) {
  const map = useMap();
  const key = points.length ? `${points[0].join(",")}:${points.length}` : "";
  useEffect(() => {
    if (points.length > 1) map.fitBounds(points, { padding: [30, 30] });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
  return null;
}

/** All routes of one plan (OPTIMIZED or BASELINE); the selected route is drawn on top and highlighted. */
export default function FleetMap({
  execs,
  selectedId,
  onSelect,
}: {
  execs: RouteExecution[];
  selectedId: string;
  onSelect: (routeId: string) => void;
}) {
  const tileUrl = useTileUrl();
  const selected = execs.find((e) => e.routeId === selectedId);
  const others = execs.filter((e) => e.routeId !== selectedId);
  const all = execs.flatMap((e) => e.path);
  const depots = new Map<string, RouteExecution>();
  execs.forEach((e) => depots.set(e.depot, e));

  return (
    <div className="health-map">
      <MapContainer center={[16.43, 102.83]} zoom={9} scrollWheelZoom>
        <FitBounds points={all} />
        <TileLayer key={tileUrl} attribution={TILE_ATTRIBUTION} url={tileUrl} />
        {others.map((e) => (
          <Polyline
            key={e.routeId}
            positions={e.path}
            pathOptions={{ color: e.color, weight: 2, opacity: selected ? 0.35 : 0.8 }}
            eventHandlers={{ click: () => onSelect(e.routeId) }}
          />
        ))}
        {selected && (
          <>
            <Polyline positions={selected.path} pathOptions={{ color: selected.color, weight: 5, opacity: 0.95 }} />
            {selected.stops
              .filter((s) => s.code !== "DEPOT")
              .map((s) => (
                <CircleMarker
                  key={`${s.seq}-${s.code}`}
                  center={[s.lat, s.lng]}
                  radius={6}
                  pathOptions={{ color: "#0b1220", weight: 1, fillColor: s.type === "Deliver" ? "#f2a900" : "#0ea5e9", fillOpacity: 0.95 }}
                >
                  <Popup>
                    <div className="popup">
                      <div className="p-title">{s.seq}. {s.location}</div>
                      <div className="p-row"><span className="lab">Node</span><span>{s.code}{s.nodeType ? ` · ${s.nodeType}` : ""}</span></div>
                      <div className="p-row"><span className="lab">Action</span><span>{s.type}</span></div>
                      <div className="p-row"><span className="lab">ETA</span><span>{s.eta}</span></div>
                      <div className="p-row"><span className="lab">Amount</span><span>{thb(Math.abs(s.amount))}</span></div>
                    </div>
                  </Popup>
                </CircleMarker>
              ))}
          </>
        )}
        {[...depots.values()].map((e) => (
          <Marker key={e.depot} position={[e.depotLat, e.depotLng]} icon={depotIcon()}>
            <Popup>
              <div className="popup">
                <div className="p-title">{e.depot}</div>
                <div className="p-row"><span className="lab">Role</span><span>Cash centre / depot</span></div>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
      <div className="map-legend map-legend-left">
        <div className="row"><span className="dot" style={{ background: "#f2a900" }} /> Deliver</div>
        <div className="row"><span className="dot" style={{ background: "#0ea5e9" }} /> Pickup</div>
        <div className="row"><span className="dot depot-legend-dot" /> Depot</div>
      </div>
    </div>
  );
}
