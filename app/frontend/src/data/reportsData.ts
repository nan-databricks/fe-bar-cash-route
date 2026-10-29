import type { AppConfig, ExecMetrics, PlanBundle, RouteExecution } from "../types";
import type { RouteTrackSummary } from "./routeExec";
import { buildExecutiveMetrics } from "./executiveOverview";
import { buildAlerts } from "./alertsData";
import { deriveMachine, generateBranchTracks } from "./tracking";
import { loadMachines } from "./machineStore";
import { thb } from "./format";

export type ReportId =
  | "daily-ops"
  | "cash-position"
  | "route-performance"
  | "exception";

export type ExportFormat = "pdf" | "excel" | "ppt";

export interface PredefinedReport {
  id: ReportId;
  title: string;
  description: string;
}

export const PREDEFINED_REPORTS: PredefinedReport[] = [
  {
    id: "daily-ops",
    title: "Daily Operations Summary",
    description: "Overview of cash and performance",
  },
  {
    id: "cash-position",
    title: "Cash Position Report",
    description: "Branch & machine cash position",
  },
  {
    id: "route-performance",
    title: "Route Performance Report",
    description: "Routes, miles, time, and cost analysis",
  },
  {
    id: "exception",
    title: "Exception Report",
    description: "Alerts and exception summary",
  },
];

export const CUSTOM_REPORT_TYPES: { id: ReportId; label: string }[] = [
  { id: "daily-ops", label: "Daily Operations Summary" },
  { id: "cash-position", label: "Cash Position Report" },
  { id: "route-performance", label: "Route Performance Report" },
  { id: "exception", label: "Exception Report" },
];

export const REGION_OPTIONS = ["All", "Khon Kaen", "DEP-KKN-C", "DEP-KKN-N", "DEP-KKN-S"];

export interface ReportContext {
  config: AppConfig;
  plan: PlanBundle;
  metrics: ExecMetrics;
  execs: RouteExecution[];
  routeSummary: RouteTrackSummary;
}

export interface ReportOptions {
  reportId: ReportId;
  format: ExportFormat;
  region: string;
  dateFrom: string;
  dateTo: string;
}

function downloadBlob(content: string, filename: string, mime: string) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function csvEscape(v: string | number): string {
  const s = String(v);
  return s.includes(",") || s.includes('"') || s.includes("\n") ? `"${s.replace(/"/g, '""')}"` : s;
}

function toCsv(headers: string[], rows: (string | number)[][]): string {
  const lines = [headers.map(csvEscape).join(",")];
  rows.forEach((r) => lines.push(r.map(csvEscape).join(",")));
  return "\uFEFF" + lines.join("\n");
}

function stamp(opts: ReportOptions): string {
  return `${opts.dateFrom}_${opts.dateTo}`.replace(/\//g, "-");
}

function reportTitle(id: ReportId): string {
  return PREDEFINED_REPORTS.find((r) => r.id === id)?.title ?? id;
}

function buildDailyOpsCsv(ctx: ReportContext, opts: ReportOptions): string {
  const eo = buildExecutiveMetrics(ctx.config, ctx.plan, ctx.metrics, ctx.execs, ctx.routeSummary);
  return toCsv(
    ["Metric", "Value", "Region", "Period"],
    [
      ["Total Cash Managed", thb(eo.totalCashManaged, false), opts.region, `${opts.dateFrom} – ${opts.dateTo}`],
      ["Idle Cash", thb(eo.idleCash, false), opts.region, ""],
      ["CIT Cost (MTD)", thb(eo.citCostMtd, false), opts.region, ""],
      ["Cash-Out Risk Machines", eo.cashOutRiskMachines, opts.region, ""],
      ["Branch Risk Count", eo.branchRisk, opts.region, ""],
      ["Route SLA %", eo.routeSla, opts.region, ""],
      ["Vehicle Utilization %", eo.vehicleUtilization, opts.region, ""],
      ["Planned Deliveries", eo.today.plannedDeliveries, opts.region, ""],
      ["Planned Pickups", eo.today.plannedPickups, opts.region, ""],
      ["Total Stops", eo.today.totalStops, opts.region, ""],
      ["Total Distance (km)", eo.today.totalDistanceKm, opts.region, ""],
      ["Total Duration (hrs)", eo.today.totalDurationH, opts.region, ""],
      ["Man-Hours Saved", ctx.metrics.manHoursSaved, opts.region, ""],
      ["Idle Cash Reduction", thb(ctx.metrics.idleCashReductionThb, false), opts.region, ""],
    ]
  );
}

function buildCashPositionCsv(ctx: ReportContext, opts: ReportOptions): string {
  const machines = loadMachines().map(deriveMachine);
  const branches = generateBranchTracks(ctx.config);
  const machineRows = machines.map((m) => [
    "Machine",
    m.id,
    m.location,
    m.currentCash,
    m.predictedEod,
    m.riskLevel,
    m.action,
    opts.region,
  ]);
  const branchRows = branches.map((b) => [
    "Branch",
    b.code,
    b.name,
    b.currentCash,
    b.currentCash + b.forecastNet,
    b.health,
    b.action,
    opts.region,
  ]);
  return toCsv(
    ["Entity Type", "ID", "Location", "Current Cash (THB)", "EOD Forecast", "Risk", "Action", "Region"],
    [...machineRows, ...branchRows]
  );
}

function buildRoutePerformanceCsv(ctx: ReportContext, opts: ReportOptions): string {
  const rs = ctx.routeSummary;
  const summaryRows: (string | number)[][] = [
    ["Fleet Summary", "", rs.totalRoutes, rs.totalStops, rs.totalDistanceKm, rs.slaPct, thb(rs.citCostThb, false), opts.region],
  ];
  const routeRows = ctx.execs.map((e) => {
    const durationH =
      Math.round((e.distanceKm / ctx.config.params.avgSpeedKmh + e.totalStops * 0.25) * 10) / 10;
    const routeCost = e.distanceKm * ctx.config.params.costPerKmThb;
    return [
      e.routeId,
      e.truckId,
      e.status,
      e.totalStops,
      e.distanceKm,
      durationH,
      thb(routeCost, false),
      `${e.completed}/${e.totalStops}`,
      opts.region,
    ];
  });
  return toCsv(
    ["Route / Section", "Truck", "Stops or Status", "Stop Count", "Distance (km)", "Duration (hrs)", "CIT Cost", "Progress", "Region"],
    [...summaryRows, ...routeRows]
  );
}

function buildExceptionCsv(ctx: ReportContext, _opts: ReportOptions): string {
  const { alerts } = buildAlerts(ctx.config, ctx.execs);
  return toCsv(
    ["Time", "Type", "Entity", "Description", "Impact", "Status"],
    alerts.map((a) => [a.time, a.type, a.entity, a.description, a.impact, a.status])
  );
}

function buildCsv(ctx: ReportContext, opts: ReportOptions): string {
  switch (opts.reportId) {
    case "daily-ops":
      return buildDailyOpsCsv(ctx, opts);
    case "cash-position":
      return buildCashPositionCsv(ctx, opts);
    case "route-performance":
      return buildRoutePerformanceCsv(ctx, opts);
    case "exception":
      return buildExceptionCsv(ctx, opts);
  }
}

function htmlShell(title: string, body: string, opts: ReportOptions): string {
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>${title}</title>
  <style>
    body { font-family: 'Segoe UI', system-ui, sans-serif; margin: 40px; color: #0f172a; }
    h1 { color: #1e3a8a; font-size: 22px; margin-bottom: 4px; }
    .meta { color: #64748b; font-size: 13px; margin-bottom: 24px; }
    table { width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 12px; }
    th, td { border: 1px solid #e2e8f0; padding: 8px 10px; text-align: left; }
    th { background: #f1f5f9; font-weight: 600; }
    tr:nth-child(even) { background: #f8fafc; }
    .kpi-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin: 16px 0; }
    .kpi { border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; }
    .kpi label { font-size: 11px; color: #64748b; text-transform: uppercase; }
    .kpi strong { display: block; font-size: 18px; margin-top: 4px; }
    @media print { body { margin: 20px; } }
  </style>
</head>
<body>
  <h1>${title}</h1>
  <div class="meta">Siam Northeast Bank · SNB Cash Logistics · ${opts.region} · ${opts.dateFrom} – ${opts.dateTo}</div>
  ${body}
  <p style="margin-top:32px;font-size:11px;color:#94a3b8">Generated ${new Date().toLocaleString()} · SNB Cash Logistics</p>
</body>
</html>`;
}

function buildPdfHtml(ctx: ReportContext, opts: ReportOptions): string {
  const title = reportTitle(opts.reportId);
  const csv = buildCsv(ctx, opts);
  const lines = csv.split("\n").slice(1);
  const rows = lines
    .filter(Boolean)
    .map((line) => {
      const cols = line.split(",").map((c) => c.replace(/^"|"$/g, "").replace(/""/g, '"'));
      return `<tr>${cols.map((c) => `<td>${c}</td>`).join("")}</tr>`;
    })
    .join("\n");
  const headers = csv
    .split("\n")[0]
    .split(",")
    .map((h) => h.replace(/^\uFEFF/, "").replace(/^"|"$/g, ""))
    .map((h) => `<th>${h}</th>`)
    .join("");

  let extra = "";
  if (opts.reportId === "daily-ops") {
    const eo = buildExecutiveMetrics(ctx.config, ctx.plan, ctx.metrics, ctx.execs, ctx.routeSummary);
    extra = `<div class="kpi-grid">
      <div class="kpi"><label>Total Cash</label><strong>${thb(eo.totalCashManaged)}</strong></div>
      <div class="kpi"><label>Route SLA</label><strong>${eo.routeSla}%</strong></div>
      <div class="kpi"><label>Utilization</label><strong>${eo.vehicleUtilization}%</strong></div>
    </div>`;
  }

  return htmlShell(title, `${extra}<table><thead><tr>${headers}</tr></thead><tbody>${rows}</tbody></table>`, opts);
}

function buildPptHtml(ctx: ReportContext, opts: ReportOptions): string {
  const title = reportTitle(opts.reportId);
  const eo = buildExecutiveMetrics(ctx.config, ctx.plan, ctx.metrics, ctx.execs, ctx.routeSummary);
  const rs = ctx.routeSummary;
  const alerts = buildAlerts(ctx.config, ctx.execs);

  const slides: string[] = [
    `<section class="slide"><h2>${title}</h2><p>${opts.region} · ${opts.dateFrom} – ${opts.dateTo}</p><p>Siam Northeast Bank · SNB Cash Logistics</p></section>`,
  ];

  if (opts.reportId === "daily-ops" || opts.reportId === "cash-position") {
    slides.push(
      `<section class="slide"><h3>Cash Overview</h3><ul>
        <li>Total cash managed: <strong>${thb(eo.totalCashManaged)}</strong></li>
        <li>Idle cash: <strong>${thb(eo.idleCash)}</strong></li>
        <li>Cash-out risk machines: <strong>${eo.cashOutRiskMachines}</strong></li>
      </ul></section>`
    );
  }
  if (opts.reportId === "daily-ops" || opts.reportId === "route-performance") {
    slides.push(
      `<section class="slide"><h3>Route Performance</h3><ul>
        <li>Routes: <strong>${rs.totalRoutes}</strong> · Stops: <strong>${rs.totalStops}</strong></li>
        <li>Distance: <strong>${rs.totalDistanceKm} km</strong></li>
        <li>SLA: <strong>${rs.slaPct}%</strong> · CIT cost: <strong>${thb(rs.citCostThb)}</strong></li>
      </ul></section>`
    );
  }
  if (opts.reportId === "exception" || opts.reportId === "daily-ops") {
    slides.push(
      `<section class="slide"><h3>Exceptions</h3><ul>
        <li>Critical: <strong>${alerts.critical}</strong> · High: <strong>${alerts.high}</strong></li>
        <li>Medium: <strong>${alerts.medium}</strong> · Total: <strong>${alerts.total}</strong></li>
      </ul></section>`
    );
  }
  slides.push(`<section class="slide"><h3>Optimization Impact</h3><ul>
    <li>Man-hours saved: <strong>${ctx.metrics.manHoursSaved} h</strong></li>
    <li>Idle cash reduction: <strong>${thb(ctx.metrics.idleCashReductionThb)}</strong></li>
    <li>Distance saved: <strong>${ctx.metrics.distanceSavedKm} km</strong></li>
  </ul></section>`);

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>${title} — Slides</title>
  <style>
    body { margin: 0; font-family: 'Segoe UI', system-ui, sans-serif; background: #0f172a; }
    .slide { min-height: 100vh; padding: 48px 56px; box-sizing: border-box; background: linear-gradient(160deg,#fff 0%,#f1f5f9 100%); border-bottom: 8px solid #1e40af; page-break-after: always; }
    .slide h2 { color: #1e3a8a; font-size: 28px; margin: 0 0 12px; }
    .slide h3 { color: #1e40af; font-size: 22px; }
    .slide ul { font-size: 18px; line-height: 1.8; }
    .slide p { color: #64748b; font-size: 16px; }
  </style>
</head>
<body>${slides.join("\n")}</body>
</html>`;
}

export function generateReport(ctx: ReportContext, opts: ReportOptions): { filename: string; message: string } {
  const base = `${opts.reportId}_${stamp(opts)}`;
  const title = reportTitle(opts.reportId);

  switch (opts.format) {
    case "excel": {
      const csv = buildCsv(ctx, opts);
      downloadBlob(csv, `${base}.csv`, "text/csv;charset=utf-8");
      return { filename: `${base}.csv`, message: `${title} exported as Excel (CSV).` };
    }
    case "pdf": {
      const html = buildPdfHtml(ctx, opts);
      downloadBlob(html, `${base}.html`, "text/html;charset=utf-8");
      return { filename: `${base}.html`, message: `${title} exported as printable HTML — open and use Print → Save as PDF.` };
    }
    case "ppt": {
      const html = buildPptHtml(ctx, opts);
      downloadBlob(html, `${base}_slides.html`, "text/html;charset=utf-8");
      return { filename: `${base}_slides.html`, message: `${title} slide deck exported — open in browser for presentation.` };
    }
  }
}
