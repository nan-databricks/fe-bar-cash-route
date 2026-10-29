/** Fetch operational data from the FastAPI backend (Unity Catalog / Lakebase / Serving / Genie, or mocks). */

import type { RouteExecution } from "../types";

export type DataSource = "unity_catalog" | "mock" | "error" | "local" | "lakebase" | "serving_endpoint" | "forecast_table" | "genie";
export type PlanType = "OPTIMIZED" | "BASELINE";

async function getJson<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(path);
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text.slice(0, 200)}`);
  }
  return (await res.json()) as T;
}

export async function fetchMachinesFromApi(): Promise<{
  source: DataSource;
  machines: unknown[];
} | null> {
  const data = await getJson<{ source: DataSource; machines: unknown[]; error?: string }>("/api/machines");
  if (!data) return null;
  if (!data.machines?.length) return null;
  return { source: data.source, machines: data.machines };
}

export async function fetchBranchesFromApi(): Promise<{
  source: DataSource;
  branches: unknown[];
} | null> {
  const data = await getJson<{ source: DataSource; branches: unknown[] }>("/api/branches");
  if (!data) return null;
  if (!data.branches?.length) return null;
  return { source: data.source, branches: data.branches };
}

export async function fetchBranchInputsFromApi(): Promise<{
  source: DataSource;
  branches: unknown[];
} | null> {
  const data = await getJson<{ source: DataSource; branches: unknown[] }>("/api/branch-inputs");
  if (!data?.branches?.length) return null;
  return { source: data.source, branches: data.branches };
}

export async function fetchRouteExecutions(planType: PlanType): Promise<{
  source: DataSource;
  routes: RouteExecution[];
} | null> {
  const data = await getJson<{ source: DataSource; routes: RouteExecution[] }>(
    `/api/route-executions?plan_type=${planType}`
  );
  if (!data?.routes?.length) return null;
  return { source: data.source, routes: data.routes };
}

export interface RouteSummaryRow {
  service_date: string;
  plan_type: PlanType;
  routes: number;
  vehicles_used: number;
  stops: number;
  km: number;
  duration_hr: number;
  cost_thb: number;
  idle_cash_thb: number;
  cashout_risk_nodes: number;
  sla_pct: number;
}

export async function fetchSummary(): Promise<{ source: DataSource; summary: RouteSummaryRow[] } | null> {
  return getJson("/api/summary");
}

export interface Health {
  status: string;
  catalog?: string;
  schema?: string;
  plan_date?: string;
  unity_catalog?: boolean;
  lakebase?: boolean;
  endpoint?: string;
  endpoint_state?: string;
  genie?: boolean;
  sources?: Record<string, string>;
}

export async function fetchHealth(): Promise<Health | null> {
  return getJson("/api/health");
}

export interface ForecastPoint {
  forecast_date: string;
  horizon_day: number;
  pred_net_outflow_thb: number;
  pred_p80_thb: number;
}

export interface ForecastResponse {
  node_id: string;
  node_type: string;
  source: DataSource;
  features_source: DataSource;
  endpoint: string;
  forecast: ForecastPoint[];
  history: { date: string; net_outflow_thb: number }[];
}

export function postForecast(nodeId: string): Promise<ForecastResponse> {
  return postJson("/api/forecast", { node_id: nodeId });
}

export interface DispatchOverride {
  override_id: number;
  service_date: string;
  route_id: string;
  node_id: string;
  action: "SKIP" | "ADD" | "RESEQUENCE" | "EMERGENCY";
  reason?: string | null;
  created_by?: string | null;
  created_at?: string | null;
}

export async function fetchOverrides(routeId?: string): Promise<{ source: DataSource; overrides: DispatchOverride[] } | null> {
  const q = routeId ? `?route_id=${encodeURIComponent(routeId)}` : "";
  return getJson(`/api/overrides${q}`);
}

export function postOverride(o: Omit<DispatchOverride, "override_id" | "created_at">): Promise<{ source: DataSource; override: DispatchOverride }> {
  return postJson("/api/overrides", o);
}

export interface GenieResponse {
  source: DataSource | "mock";
  conversation_id: string;
  message_id: string;
  status: string;
  text: string;
  sql?: string | null;
  columns: string[];
  rows: unknown[][];
  note?: string;
}

export function askGenie(question: string, conversationId?: string): Promise<GenieResponse> {
  return postJson("/api/genie/ask", { question, conversation_id: conversationId });
}
