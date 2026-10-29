import { useEffect } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from "react-leaflet";
import type { Health } from "../types";
import { HEALTH_COLOR } from "../data/tracking";
import { TILE_ATTRIBUTION, useTileUrl } from "../hooks/useTheme";

export interface MapPoint {
  id: string;
  lat: number;
  lng: number;
  health: Health;
  title: string;
  rows: [string, string][];
  emphasize?: boolean;
  kind?: "machine" | "branch";
}

function FitBounds({ points }: { points: MapPoint[] }) {
  const map = useMap();
  const key = points.map((p) => `${p.lat},${p.lng}`).join(";");
  useEffect(() => {
    if (points.length === 1) map.setView([points[0].lat, points[0].lng], 12);
    else if (points.length > 1)
      map.fitBounds(points.map((p) => [p.lat, p.lng]), { padding: [50, 50] });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
  return null;
}

export default function HealthMap({
  points,
  showEmergencyLegend = false,
  showKindLegend = false,
}: {
  points: MapPoint[];
  showEmergencyLegend?: boolean;
  showKindLegend?: boolean;
}) {
  const tileUrl = useTileUrl();
  return (
    <div className="health-map">
      <MapContainer center={[16.44, 102.83]} zoom={11} scrollWheelZoom>
        <FitBounds points={points} />
        <TileLayer key={tileUrl} attribution={TILE_ATTRIBUTION} url={tileUrl} />
        {points.map((p) => (
          <CircleMarker
            key={p.id}
            center={[p.lat, p.lng]}
            radius={p.emphasize ? 8 : p.kind === "branch" ? 7 : 6}
            pathOptions={{
              color: p.emphasize ? "#fff" : HEALTH_COLOR[p.health],
              weight: p.emphasize ? 2 : p.kind === "machine" ? 2 : 1,
              fillColor: HEALTH_COLOR[p.health],
              fillOpacity: p.kind === "branch" ? 0.75 : 0.85,
              dashArray: p.kind === "machine" ? "2 2" : undefined,
            }}
          >
            <Popup>
              <div className="popup">
                <div className="p-title">{p.title}</div>
                {p.rows.map(([lab, val], i) => (
                  <div className="p-row" key={i}>
                    <span className="lab">{lab}</span>
                    <span>{val}</span>
                  </div>
                ))}
              </div>
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>
      <div className="map-legend">
        {(Object.keys(HEALTH_COLOR) as Health[]).map((h) => (
          <div className="row" key={h}>
            <span className="dot" style={{ background: HEALTH_COLOR[h] }} /> {h}
          </div>
        ))}
        {showKindLegend && (
          <>
            <div className="row legend-sep" />
            <div className="row">
              <span className="dot kind-machine" /> Machine
            </div>
            <div className="row">
              <span className="dot kind-branch" /> Branch
            </div>
          </>
        )}
        {showEmergencyLegend && (
          <div className="row">
            <span className="dot emergency-dot" /> Emergency
          </div>
        )}
      </div>
    </div>
  );
}
