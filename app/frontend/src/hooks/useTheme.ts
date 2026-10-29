import { useEffect, useState } from "react";

export type Theme = "dark" | "light";

function currentTheme(): Theme {
  return (document.documentElement.getAttribute("data-theme") as Theme) || "dark";
}

/** Tracks the active theme by observing the `data-theme` attribute on <html>. */
export function useTheme(): Theme {
  const [theme, setTheme] = useState<Theme>(currentTheme);

  useEffect(() => {
    const obs = new MutationObserver(() => setTheme(currentTheme()));
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => obs.disconnect();
  }, []);

  return theme;
}

const OSM_TILES = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
export const TILE_ATTRIBUTION = "&copy; <a href=\"https://www.openstreetmap.org/copyright\">OpenStreetMap</a> contributors";

/** OpenStreetMap tiles for both themes (dark theme darkens them via CSS on .leaflet-tile-pane). */
export function useTileUrl(): string {
  useTheme();
  return OSM_TILES;
}
