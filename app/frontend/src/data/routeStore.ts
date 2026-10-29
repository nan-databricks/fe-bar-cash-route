const STORAGE_KEY = "snb-route-input-v1";

/** Custom route-plan JSON supplied by the user, or null to use the generated plan. */
export function loadRouteInput(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

export function saveRouteInput(json: string): void {
  try {
    localStorage.setItem(STORAGE_KEY, json);
  } catch {
    /* ignore */
  }
}

export function clearRouteInput(): void {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* ignore */
  }
}
