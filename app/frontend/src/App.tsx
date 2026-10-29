import { useEffect, useMemo, useState } from "react";
import {
  LayoutDashboard,
  Cpu,
  Building2,
  Route as RouteIcon,
  Truck,
  Sun,
  Moon,
  LayoutGrid,
  Brain,
  AlertTriangle,
  FlaskConical,
  FileDown,
  PanelLeftClose,
  PanelLeftOpen,
  Sparkles,
} from "lucide-react";
import type { AppConfig, BranchInput, BranchTrack, Machine, RouteExecution } from "./types";
import { buildPlanFromConfig } from "./data/mockData";
import { buildRouteExecutions, summarizeRoutes } from "./data/routeExec";
import { loadConfig } from "./data/configStore";
import {
  fetchBranchInputsFromApi,
  fetchBranchesFromApi,
  fetchHealth,
  fetchMachinesFromApi,
  fetchRouteExecutions,
  fetchSummary,
  type Health,
  type PlanType,
  type RouteSummaryRow,
} from "./data/api";
import GeniePage from "./components/GeniePage";
import KpiCards from "./components/KpiCards";
import MapView from "./components/MapView";
import ComparisonChart from "./components/ComparisonChart";
import BranchTable from "./components/BranchTable";
import RoutePanel from "./components/RoutePanel";
import ExecutiveOverviewPage from "./components/ExecutiveOverviewPage";
import AiPerformancePage from "./components/AiPerformancePage";
import AlertsPage from "./components/AlertsPage";
import ScenarioPage from "./components/ScenarioPage";
import ReportsPage from "./components/ReportsPage";
import MachineTrackingPage from "./components/MachineTrackingPage";
import BranchTrackingPage from "./components/BranchTrackingPage";
import RouteTrackingPage from "./components/RouteTrackingPage";
import RouteDetailPage from "./components/RouteDetailPage";
import { thb } from "./data/format";

type View =
  | "overview"
  | "dashboard"
  | "machines"
  | "branches"
  | "routes"
  | "detail"
  | "ai"
  | "alerts"
  | "scenario"
  | "reports"
  | "genie";

const NAV_ITEMS: { id: View; label: string; icon: typeof Cpu }[] = [
  { id: "overview", label: "Overview", icon: LayoutGrid },
  { id: "machines", label: "Machines", icon: Cpu },
  { id: "branches", label: "Branches", icon: Building2 },
  { id: "routes", label: "Route Tracking", icon: RouteIcon },
  { id: "detail", label: "Truck Detail", icon: Truck },
  { id: "dashboard", label: "Optimization", icon: LayoutDashboard },
  { id: "ai", label: "AI Performance", icon: Brain },
  { id: "alerts", label: "Alerts", icon: AlertTriangle },
  { id: "scenario", label: "Scenario", icon: FlaskConical },
  { id: "reports", label: "Reports", icon: FileDown },
  { id: "genie", label: "Ask SNB Ops", icon: Sparkles },
];

type Theme = "dark" | "light";

export default function App() {
  const [config, setConfig] = useState<AppConfig>(() => loadConfig());
  const [view, setView] = useState<View>(() => {
    const v = new URLSearchParams(window.location.search).get("view") as View | null;
    return v && NAV_ITEMS.some((n) => n.id === v) ? v : "overview";
  });
  const [showOptimized, setShowOptimized] = useState(true);
  const [showOriginal, setShowOriginal] = useState(true);
  const [theme, setTheme] = useState<Theme>(
    () => (localStorage.getItem("snb-theme") as Theme) || "dark"
  );
  const [navCollapsed, setNavCollapsed] = useState<boolean>(
    () => localStorage.getItem("snb-nav-collapsed") === "1"
  );
  const [detailRouteId, setDetailRouteId] = useState<string>("");
  const [ucMachines, setUcMachines] = useState<Machine[] | null>(null);
  const [ucBranchTracks, setUcBranchTracks] = useState<BranchTrack[] | null>(null);
  const [ucRoutes, setUcRoutes] = useState<Partial<Record<PlanType, RouteExecution[]>>>({});
  const [planType, setPlanType] = useState<PlanType>("OPTIMIZED");
  const [summaryRows, setSummaryRows] = useState<RouteSummaryRow[]>([]);
  const [summarySource, setSummarySource] = useState<string>("");
  const [health, setHealth] = useState<Health | null>(null);
  const [dataSourceLabel, setDataSourceLabel] = useState("Connecting…");

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("snb-theme", theme);
  }, [theme]);

  useEffect(() => {
    localStorage.setItem("snb-nav-collapsed", navCollapsed ? "1" : "0");
  }, [navCollapsed]);

  const plan = useMemo(() => buildPlanFromConfig(config), [config]);
  const { branches, optimized, original, metrics } = plan;
  const generatedExecs = useMemo(
    () => buildRouteExecutions(plan, config.params),
    [plan, config.params]
  );
  const liveExecs = ucRoutes.OPTIMIZED ?? generatedExecs;
  const planExecs = ucRoutes[planType] ?? liveExecs;
  const liveRouteSummary = useMemo(
    () => summarizeRoutes(liveExecs, plan, config.params),
    [liveExecs, plan, config.params]
  );
  const planRouteSummary = useMemo(
    () => summarizeRoutes(planExecs, plan, config.params),
    [planExecs, plan, config.params]
  );

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const [h, m, b, bi, ro, rb, sm] = await Promise.all([
        fetchHealth(),
        fetchMachinesFromApi(),
        fetchBranchesFromApi(),
        fetchBranchInputsFromApi(),
        fetchRouteExecutions("OPTIMIZED"),
        fetchRouteExecutions("BASELINE"),
        fetchSummary(),
      ]);
      if (cancelled) return;
      setHealth(h);
      if (sm?.summary?.length) {
        setSummaryRows(sm.summary);
        setSummarySource(sm.source);
      }

      if (m?.machines?.length) {
        setUcMachines(m.machines as Machine[]);
      }
      if (b?.branches?.length) {
        setUcBranchTracks(b.branches as BranchTrack[]);
      }
      if (bi?.branches?.length) {
        setConfig((prev) => ({
          ...prev,
          branches: bi.branches as BranchInput[],
          params: {
            ...prev.params,
            planDate: h?.plan_date ?? prev.params.planDate,
          },
        }));
      }
      setUcRoutes({
        ...(ro?.routes?.length ? { OPTIMIZED: ro.routes } : {}),
        ...(rb?.routes?.length ? { BASELINE: rb.routes } : {}),
      });

      if (!h) setDataSourceLabel("Offline · browser mock");
      else if (h.unity_catalog) setDataSourceLabel(`UC · ${h.schema ?? "snb_cash_ops"}`);
      else setDataSourceLabel("Mock · SNB fixtures");
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className={`app ${navCollapsed ? "nav-collapsed" : ""}`}>
      <aside className="sidebar">
        <div className="sidebar-top">
          <div className="brand">
            <div className="logo">
              <img src="/snb-logo.svg" alt="Siam Northeast Bank" />
            </div>
            <div className="brand-text">
              <h1>SNB Cash Logistics</h1>
              <div className="sub">Khon Kaen · CVRP-TW</div>
            </div>
          </div>
          <button
            className="sidebar-toggle"
            onClick={() => setNavCollapsed((c) => !c)}
            title={navCollapsed ? "Expand navigation" : "Collapse navigation"}
            aria-label="Toggle navigation"
          >
            {navCollapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
          </button>
        </div>

        <nav className="nav-tabs">
          {NAV_ITEMS.map((t) => {
            const Icon = t.icon;
            return (
              <button
                key={t.id}
                className={`nav-tab ${view === t.id ? "active" : ""}`}
                onClick={() => setView(t.id)}
                title={t.label}
              >
                <Icon size={18} />
                <span className="nav-label">{t.label}</span>
              </button>
            );
          })}
        </nav>

        <div className="sidebar-bottom">
          <span
            className="pill"
            title={health ? `UC: ${health.unity_catalog ? "live" : "mock"} · Lakebase: ${health.lakebase ? "live" : "mock"} · Serving: ${health.endpoint_state ?? "-"} · Genie: ${health.genie ? "live" : "mock"}` : dataSourceLabel}
          >
            <span className="pill-dot">●</span>
            <span className="nav-label">{dataSourceLabel}</span>
          </span>
          <button
            className="theme-toggle"
            onClick={() => setTheme((t) => (t === "dark" ? "light" : "dark"))}
            title={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
            aria-label="Toggle theme"
          >
            {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
          </button>
        </div>
      </aside>

      <main className="main-col">
        {view === "overview" ? (
          <div className="dash-scroll">
            <ExecutiveOverviewPage
              config={config}
              plan={plan}
              metrics={metrics}
              execs={liveExecs}
              routeSummary={liveRouteSummary}
              machinesOverride={ucMachines ?? undefined}
              branchTracksOverride={ucBranchTracks ?? undefined}
            />
          </div>
        ) : view === "machines" ? (
          <div className="dash-scroll">
            <MachineTrackingPage machinesOverride={ucMachines ?? undefined} />
          </div>
        ) : view === "branches" ? (
          <div className="dash-scroll">
            <BranchTrackingPage
              config={config}
              tracksOverride={ucBranchTracks ?? undefined}
            />
          </div>
        ) : view === "routes" ? (
          <div className="dash-scroll">
            <RouteTrackingPage
              execs={planExecs}
              summary={planRouteSummary}
              planType={planType}
              onPlanChange={setPlanType}
              summaryRows={summaryRows}
              summarySource={summarySource}
              onOpenDetail={(id) => {
                setDetailRouteId(id);
                setView("detail");
              }}
            />
          </div>
        ) : view === "detail" ? (
          <div className="dash-scroll">
            <RouteDetailPage
              key={detailRouteId}
              execs={planExecs}
              initialRouteId={detailRouteId}
              planType={planType}
              onPlanChange={setPlanType}
              serviceDate={health?.plan_date ?? config.params.planDate}
            />
          </div>
        ) : view === "ai" ? (
          <div className="dash-scroll">
            <AiPerformancePage metrics={metrics} />
          </div>
        ) : view === "alerts" ? (
          <div className="dash-scroll">
            <AlertsPage config={config} execs={liveExecs} />
          </div>
        ) : view === "scenario" ? (
          <div className="dash-scroll">
            <ScenarioPage
              config={config}
              onApplyScenario={(c) => {
                setConfig(c);
                setView("overview");
              }}
            />
          </div>
        ) : view === "genie" ? (
          <div className="dash-scroll">
            <GeniePage />
          </div>
        ) : view === "reports" ? (
          <div className="dash-scroll">
            <ReportsPage
              config={config}
              plan={plan}
              metrics={metrics}
              execs={liveExecs}
              routeSummary={liveRouteSummary}
            />
          </div>
        ) : (
          <div className="dash-scroll">
            <section className="map-hero">
              <MapView
                key={`${branches.length}-${config.params.numVans}`}
                branches={branches}
                optimized={optimized}
                original={original}
                showOptimized={showOptimized}
                showOriginal={showOriginal}
                onToggleOptimized={() => setShowOptimized((s) => !s)}
                onToggleOriginal={() => setShowOriginal((s) => !s)}
              />

              <div className="kpi-ribbon">
                <RibbonStat
                  label="Man-hours saved"
                  value={`${metrics.manHoursSaved} h`}
                  sub={`▼ ${metrics.manHoursSavedPct}%`}
                  accent="#4ade80"
                />
                <RibbonStat
                  label="Idle cash freed"
                  value={thb(metrics.idleCashReductionThb)}
                  sub={`▼ ${metrics.idleCashReductionPct}%`}
                  accent="#38bdf8"
                />
                <RibbonStat
                  label="Distance reduced"
                  value={`${metrics.distanceSavedKm} km`}
                  sub={`▼ ${metrics.distanceSavedPct}%`}
                  accent="#38bdf8"
                />
                <RibbonStat
                  label="Cost saved / day"
                  value={thb(metrics.fuelCostSavedThb)}
                  sub={`${metrics.branchesServed}/${metrics.branchesTotal} branches`}
                  accent="#f59e0b"
                />
              </div>

              <div className="dispatch-overlay">
                <RoutePanel plan={optimized} branches={branches} />
              </div>
            </section>

            <div className="analytics">
              <KpiCards m={metrics} />

              <div className="panel">
                <div className="panel-head">
                  <h2>Optimized vs Actual — Operational Comparison</h2>
                  <span className="hint">
                    {metrics.distanceSavedKm} km &amp; {metrics.manHoursSaved}h saved per cycle
                  </span>
                </div>
                <div className="panel-body">
                  <ComparisonChart optimized={optimized} original={original} />
                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "repeat(3,1fr)",
                      gap: 12,
                      marginTop: 14,
                      fontSize: 12,
                    }}
                  >
                    <SummaryStat
                      label="Actual plan"
                      value={`${original.totalDistanceKm} km · ${original.vehiclesUsed} van`}
                      color="#ef4444"
                    />
                    <SummaryStat
                      label="Optimized plan"
                      value={`${optimized.totalDistanceKm} km · ${optimized.vehiclesUsed} vans`}
                      color="#22c55e"
                    />
                    <SummaryStat
                      label="Idle cash freed"
                      value={thb(metrics.idleCashReductionThb)}
                      color="#38bdf8"
                    />
                  </div>
                </div>
              </div>

              <BranchTable branches={branches} />
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

function RibbonStat({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string;
  sub: string;
  accent: string;
}) {
  return (
    <div className="ribbon-stat">
      <div className="r-label">{label}</div>
      <div className="r-value" style={{ color: accent }}>
        {value}
      </div>
      <div className="r-sub">{sub}</div>
    </div>
  );
}

function SummaryStat({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div
      style={{
        border: "1px solid var(--border)",
        borderRadius: 10,
        padding: "10px 12px",
        borderLeft: `3px solid ${color}`,
      }}
    >
      <div style={{ color: "var(--muted)", fontSize: 10, textTransform: "uppercase", letterSpacing: 0.5 }}>
        {label}
      </div>
      <div style={{ fontWeight: 700, marginTop: 4 }}>{value}</div>
    </div>
  );
}
