import { useState } from "react";
import { FileText, Download, Calendar, CheckCircle2 } from "lucide-react";
import type { AppConfig, ExecMetrics, PlanBundle, RouteExecution } from "../types";
import type { RouteTrackSummary } from "../data/routeExec";
import {
  PREDEFINED_REPORTS,
  CUSTOM_REPORT_TYPES,
  REGION_OPTIONS,
  generateReport,
  type ReportId,
  type ExportFormat,
  type ReportContext,
} from "../data/reportsData";

function ReportIllustration() {
  return (
    <svg className="reports-illustration" viewBox="0 0 200 160" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden>
      <rect x="20" y="30" width="90" height="110" rx="6" fill="var(--panel-2)" stroke="var(--border)" strokeWidth="1.5" />
      <rect x="32" y="44" width="66" height="8" rx="2" fill="#2563eb" opacity="0.7" />
      <rect x="32" y="58" width="50" height="5" rx="1.5" fill="var(--muted)" opacity="0.4" />
      <circle cx="58" cy="88" r="22" fill="#dbeafe" stroke="#2563eb" strokeWidth="2" />
      <path d="M58 76 L58 88 L68 94" stroke="#2563eb" strokeWidth="2.5" strokeLinecap="round" />
      <rect x="38" y="118" width="12" height="14" rx="2" fill="#22c55e" />
      <rect x="54" y="110" width="12" height="22" rx="2" fill="#2563eb" />
      <rect x="70" y="114" width="12" height="18" rx="2" fill="#f59e0b" />
      <rect x="55" y="10" width="95" height="115" rx="6" fill="var(--panel)" stroke="var(--border)" strokeWidth="1.5" />
      <rect x="68" y="24" width="70" height="8" rx="2" fill="#1e40af" opacity="0.8" />
      <rect x="68" y="38" width="55" height="5" rx="1.5" fill="var(--muted)" opacity="0.35" />
      <rect x="72" y="55" width="10" height="28" rx="2" fill="#3b82f6" />
      <rect x="86" y="48" width="10" height="35" rx="2" fill="#60a5fa" />
      <rect x="100" y="62" width="10" height="21" rx="2" fill="#93c5fd" />
      <rect x="114" y="52" width="10" height="31" rx="2" fill="#2563eb" />
      <circle cx="130" cy="105" r="14" fill="#dcfce7" stroke="#22c55e" strokeWidth="1.5" />
      <path d="M124 105 L128 109 L136 99" stroke="#22c55e" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default function ReportsPage({
  config,
  plan,
  metrics,
  execs,
  routeSummary,
}: {
  config: AppConfig;
  plan: PlanBundle;
  metrics: ExecMetrics;
  execs: RouteExecution[];
  routeSummary: RouteTrackSummary;
}) {
  const ctx: ReportContext = { config, plan, metrics, execs, routeSummary };
  const defaultDate = config.params.planDate || "21 May 2025";

  const [customType, setCustomType] = useState<ReportId>("daily-ops");
  const [region, setRegion] = useState("All");
  const [dateFrom, setDateFrom] = useState("2025-05-20");
  const [dateTo, setDateTo] = useState("2025-05-20");
  const [format, setFormat] = useState<ExportFormat>("excel");
  const [toast, setToast] = useState<string | null>(null);
  const [generating, setGenerating] = useState<string | null>(null);

  const fmtDisplay = (iso: string) => {
    const [y, m, d] = iso.split("-");
    return `${d}/${m}/${y}`;
  };

  const run = (reportId: ReportId, fmt: ExportFormat = "excel") => {
    setGenerating(reportId);
    const result = generateReport(ctx, {
      reportId,
      format: fmt,
      region,
      dateFrom: fmtDisplay(dateFrom),
      dateTo: fmtDisplay(dateTo),
    });
    setToast(result.message);
    setGenerating(null);
    setTimeout(() => setToast(null), 5000);
  };

  return (
    <div className="reports-page">
      {toast && (
        <div className="reports-toast">
          <CheckCircle2 size={16} />
          {toast}
        </div>
      )}

      <section className="reports-section">
        <h2 className="reports-section-title">Predefined Reports</h2>
        <div className="reports-predefined-grid">
          {PREDEFINED_REPORTS.map((r) => (
            <div className="reports-card" key={r.id}>
              <FileText size={22} className="reports-card-icon" />
              <h3>{r.title}</h3>
              <p>{r.description}</p>
              <button
                type="button"
                className="btn primary reports-gen-btn"
                disabled={generating === r.id}
                onClick={() => run(r.id, "excel")}
              >
                <Download size={14} />
                {generating === r.id ? "Generating…" : "Generate"}
              </button>
            </div>
          ))}
        </div>
      </section>

      <section className="reports-section panel reports-custom">
        <h2 className="reports-section-title">Custom Report Builder</h2>
        <div className="reports-custom-body">
          <div className="reports-custom-fields">
            <div className="reports-field">
              <label>Report Type</label>
              <select
                className="select-inline reports-select"
                value={customType}
                onChange={(e) => setCustomType(e.target.value as ReportId)}
              >
                <option value="" disabled>
                  Select Report
                </option>
                {CUSTOM_REPORT_TYPES.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="reports-field">
              <label>Region</label>
              <select className="select-inline reports-select" value={region} onChange={(e) => setRegion(e.target.value)}>
                {REGION_OPTIONS.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </select>
            </div>

            <div className="reports-field">
              <label>Date Range</label>
              <div className="reports-date-range">
                <Calendar size={15} className="reports-cal-icon" />
                <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="reports-date" />
                <span className="reports-date-sep">–</span>
                <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="reports-date" />
              </div>
              <span className="reports-date-hint">Plan date: {defaultDate}</span>
            </div>

            <div className="reports-field">
              <label>Output Format</label>
              <div className="reports-format-row">
                {(
                  [
                    { id: "pdf" as const, label: "PDF", cls: "fmt-pdf" },
                    { id: "excel" as const, label: "Excel", cls: "fmt-excel" },
                    { id: "ppt" as const, label: "PowerPoint", cls: "fmt-ppt" },
                  ] as const
                ).map((f) => (
                  <button
                    key={f.id}
                    type="button"
                    className={`reports-format-btn ${f.cls} ${format === f.id ? "active" : ""}`}
                    onClick={() => setFormat(f.id)}
                  >
                    {f.label}
                  </button>
                ))}
              </div>
            </div>

            <button
              type="button"
              className="btn primary reports-custom-gen"
              disabled={!customType || generating === customType}
              onClick={() => customType && run(customType, format)}
            >
              <Download size={15} />
              Generate Custom Report
            </button>
          </div>

          <div className="reports-custom-art">
            <ReportIllustration />
          </div>
        </div>
      </section>
    </div>
  );
}
