import { useRef } from "react";
import {
  Plus,
  Trash2,
  Play,
  RotateCcw,
  Download,
  Upload,
  FileJson,
  FileSpreadsheet,
} from "lucide-react";
import type { AppConfig, BranchInput, OptimizerParams } from "../types";
import { computeBranch } from "../data/mockData";
import {
  branchesToCsv,
  csvToBranches,
  download,
  exportConfigJson,
  resetConfig,
} from "../data/configStore";

const STATUS_COLOR: Record<string, string> = {
  REPLENISH: "#f59e0b",
  PICKUP: "#0ea5e9",
  OK: "#64748b",
};

interface Props {
  config: AppConfig;
  onChange: (c: AppConfig) => void;
  onApply: () => void;
}

const NUM_PARAM_FIELDS: { key: keyof OptimizerParams; label: string; step?: number }[] = [
  { key: "numVans", label: "Number of vans" },
  { key: "vanCashCapacity", label: "Van cash capacity (฿)", step: 1_000_000 },
  { key: "avgSpeedKmh", label: "Avg speed (km/h)" },
  { key: "roadFactor", label: "Road factor", step: 0.01 },
  { key: "costPerKmThb", label: "Cost per km (฿)" },
  { key: "co2PerKmKg", label: "CO₂ per km (kg)", step: 0.01 },
  { key: "crewPerVehicle", label: "Crew per van" },
  { key: "cityServiceMin", label: "City service (min)" },
  { key: "districtServiceMin", label: "District service (min)" },
  { key: "replenishTargetPct", label: "Replenish target (0-1)", step: 0.05 },
  { key: "excessLinePct", label: "Excess trigger (0-1)", step: 0.05 },
  { key: "keepPct", label: "Keep after pickup (0-1)", step: 0.05 },
];

export default function InputPage({ config, onChange, onApply }: Props) {
  const jsonInputRef = useRef<HTMLInputElement>(null);
  const csvInputRef = useRef<HTMLInputElement>(null);

  const setParam = (key: keyof OptimizerParams, value: string | number) => {
    onChange({ ...config, params: { ...config.params, [key]: value } });
  };

  const setBranchField = (idx: number, key: keyof BranchInput, value: string | number | boolean) => {
    const branches = config.branches.map((b, i) => (i === idx ? { ...b, [key]: value } : b));
    onChange({ ...config, branches });
  };

  const addBranch = () => {
    const b: BranchInput = {
      code: `B${config.branches.length}`,
      name: "New Branch",
      district: "Mueang Khon Kaen",
      lat: 16.43,
      lng: 102.83,
      cashCapacity: 12_000_000,
      minThreshold: 1_800_000,
      openingCash: 6_000_000,
      predictedInflow: 2_000_000,
      predictedOutflow: 2_000_000,
    };
    onChange({ ...config, branches: [...config.branches, b] });
  };

  const removeBranch = (idx: number) => {
    onChange({ ...config, branches: config.branches.filter((_, i) => i !== idx) });
  };

  const handleImportJson = (file: File) => {
    file.text().then((txt) => {
      try {
        const parsed = JSON.parse(txt) as Partial<AppConfig>;
        onChange({
          params: { ...config.params, ...(parsed.params ?? {}) },
          branches: parsed.branches ?? config.branches,
        });
      } catch {
        alert("Invalid JSON config file.");
      }
    });
  };

  const handleImportCsv = (file: File) => {
    file.text().then((txt) => {
      try {
        const branches = csvToBranches(txt);
        if (!branches.length) throw new Error("empty");
        onChange({ ...config, branches });
      } catch {
        alert("Could not parse CSV. Check the header row matches the documented format.");
      }
    });
  };

  const derived = config.branches.map((b) => computeBranch(b, config.params));
  const actionable = derived.filter((d) => !d.isDepot && d.status !== "OK").length;

  return (
    <div className="config-page">
      <div className="config-main">
        {/* Toolbar */}
        <div className="panel">
          <div className="panel-body toolbar">
            <button className="btn primary" onClick={onApply}>
              <Play size={15} /> Generate plan &amp; view dashboard
            </button>
            <span style={{ color: "var(--muted)", fontSize: 12 }}>
              {config.branches.filter((b) => !b.isDepot).length} branches · {actionable} require action ·{" "}
              {config.params.numVans} vans
            </span>
            <div style={{ flex: 1 }} />
            <button className="btn sm" onClick={() => download("snb-config.json", exportConfigJson(config), "application/json")}>
              <Download size={14} /> JSON
            </button>
            <button className="btn sm" onClick={() => jsonInputRef.current?.click()}>
              <Upload size={14} /> JSON
            </button>
            <button className="btn sm" onClick={() => download("snb-branches.csv", branchesToCsv(config.branches), "text/csv")}>
              <Download size={14} /> CSV
            </button>
            <button className="btn sm" onClick={() => csvInputRef.current?.click()}>
              <Upload size={14} /> CSV
            </button>
            <button className="btn sm danger" onClick={() => onChange(resetConfig())}>
              <RotateCcw size={14} /> Reset
            </button>
            <input
              ref={jsonInputRef}
              type="file"
              accept=".json,application/json"
              className="hidden-file"
              onChange={(e) => e.target.files?.[0] && handleImportJson(e.target.files[0])}
            />
            <input
              ref={csvInputRef}
              type="file"
              accept=".csv,text/csv"
              className="hidden-file"
              onChange={(e) => e.target.files?.[0] && handleImportCsv(e.target.files[0])}
            />
          </div>
        </div>

        {/* Optimizer parameters */}
        <div className="panel">
          <div className="panel-head">
            <h2>Optimizer &amp; Cost Parameters</h2>
            <span className="hint">CVRP-TW + cost model settings</span>
          </div>
          <div className="panel-body">
            <div className="form-grid">
              <div className="field">
                <label>Plan date</label>
                <input value={config.params.planDate} onChange={(e) => setParam("planDate", e.target.value)} />
              </div>
              <div className="field" style={{ gridColumn: "span 2" }}>
                <label>Region</label>
                <input value={config.params.region} onChange={(e) => setParam("region", e.target.value)} />
              </div>
              <div className="field">
                <label>Idle-cash residual (0-1)</label>
                <input
                  type="number"
                  step={0.01}
                  value={config.params.idleCashResidualPct}
                  onChange={(e) => setParam("idleCashResidualPct", Number(e.target.value))}
                />
              </div>
              {NUM_PARAM_FIELDS.map((f) => (
                <div className="field" key={f.key}>
                  <label>{f.label}</label>
                  <input
                    type="number"
                    step={f.step ?? 1}
                    value={config.params[f.key] as number}
                    onChange={(e) => setParam(f.key, Number(e.target.value))}
                  />
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Branch editor */}
        <div className="panel">
          <div className="panel-head">
            <h2>Branch &amp; ML Forecast Inputs</h2>
            <button className="btn sm" onClick={addBranch}>
              <Plus size={14} /> Add branch
            </button>
          </div>
          <div className="panel-body edit-table-wrap" style={{ maxHeight: 460, overflowY: "auto" }}>
            <table className="edit-table">
              <thead>
                <tr>
                  <th>Code</th>
                  <th>Name</th>
                  <th>District</th>
                  <th>Lat</th>
                  <th>Lng</th>
                  <th>Depot</th>
                  <th>Capacity</th>
                  <th>Min thr.</th>
                  <th>Opening</th>
                  <th>Pred. inflow</th>
                  <th>Pred. outflow</th>
                  <th>Status</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {config.branches.map((b, i) => {
                  const d = derived[i];
                  return (
                    <tr key={i}>
                      <td><input className="w-code" value={b.code} onChange={(e) => setBranchField(i, "code", e.target.value)} /></td>
                      <td><input value={b.name} onChange={(e) => setBranchField(i, "name", e.target.value)} style={{ minWidth: 150 }} /></td>
                      <td><input value={b.district} onChange={(e) => setBranchField(i, "district", e.target.value)} style={{ minWidth: 120 }} /></td>
                      <td><input className="num" type="number" step={0.0001} value={b.lat} onChange={(e) => setBranchField(i, "lat", Number(e.target.value))} style={{ width: 80 }} /></td>
                      <td><input className="num" type="number" step={0.0001} value={b.lng} onChange={(e) => setBranchField(i, "lng", Number(e.target.value))} style={{ width: 80 }} /></td>
                      <td style={{ textAlign: "center" }}>
                        <input type="checkbox" checked={!!b.isDepot} onChange={(e) => setBranchField(i, "isDepot", e.target.checked)} />
                      </td>
                      <td><input className="num" type="number" step={1_000_000} value={b.cashCapacity} onChange={(e) => setBranchField(i, "cashCapacity", Number(e.target.value))} style={{ width: 110 }} /></td>
                      <td><input className="num" type="number" step={100_000} value={b.minThreshold} onChange={(e) => setBranchField(i, "minThreshold", Number(e.target.value))} style={{ width: 100 }} /></td>
                      <td><input className="num" type="number" step={100_000} value={b.openingCash} onChange={(e) => setBranchField(i, "openingCash", Number(e.target.value))} style={{ width: 110 }} /></td>
                      <td><input className="num" type="number" step={100_000} value={b.predictedInflow} onChange={(e) => setBranchField(i, "predictedInflow", Number(e.target.value))} style={{ width: 110 }} /></td>
                      <td><input className="num" type="number" step={100_000} value={b.predictedOutflow} onChange={(e) => setBranchField(i, "predictedOutflow", Number(e.target.value))} style={{ width: 110 }} /></td>
                      <td style={{ whiteSpace: "nowrap" }}>
                        {b.isDepot ? (
                          <span style={{ color: "var(--muted)" }}>Depot</span>
                        ) : (
                          <>
                            <span className="status-dot" style={{ background: STATUS_COLOR[d.status] }} />
                            {d.status === "REPLENISH" ? "Replenish" : d.status === "PICKUP" ? "Pickup" : "OK"}
                          </>
                        )}
                      </td>
                      <td>
                        <button className="icon-btn" onClick={() => removeBranch(i)} title="Remove branch">
                          <Trash2 size={14} />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Format documentation */}
      <div className="panel" style={{ alignSelf: "start" }}>
        <div className="panel-head">
          <h2>Input Formats</h2>
        </div>
        <div className="panel-body format-doc">
          <p style={{ color: "var(--muted)", marginTop: 0 }}>
            Provide inputs by editing the tables, or import a file. All derived values (status,
            demand, routes, KPIs) are computed from these fields.
          </p>

          <h3><FileSpreadsheet size={12} style={{ verticalAlign: "-2px" }} /> Branch CSV</h3>
          <p>First row must be the header, exactly:</p>
          <pre>{`code,name,district,lat,lng,
isDepot,cashCapacity,minThreshold,
openingCash,predictedInflow,
predictedOutflow`}</pre>
          <table className="schema">
            <tbody>
              <tr><td>code</td><td>Unique branch code (string)</td></tr>
              <tr><td>name</td><td>Branch display name</td></tr>
              <tr><td>district</td><td>"Mueang Khon Kaen" = city (shorter dwell)</td></tr>
              <tr><td>lat, lng</td><td>WGS84 decimal degrees</td></tr>
              <tr><td>isDepot</td><td>true for the cash center (one row)</td></tr>
              <tr><td>cashCapacity</td><td>Vault capacity, THB</td></tr>
              <tr><td>minThreshold</td><td>Min operating cash, THB</td></tr>
              <tr><td>openingCash</td><td>Start-of-day balance, THB</td></tr>
              <tr><td>predictedInflow</td><td>ML model output, THB</td></tr>
              <tr><td>predictedOutflow</td><td>ML model output, THB</td></tr>
            </tbody>
          </table>

          <h3>How status is derived</h3>
          <p>
            <code>closing = openingCash + inflow − outflow</code>
          </p>
          <table className="schema">
            <tbody>
              <tr><td>REPLENISH</td><td>closing &lt; minThreshold</td></tr>
              <tr><td>PICKUP</td><td>closing &gt; capacity × excessTrigger</td></tr>
              <tr><td>OK</td><td>otherwise → not visited</td></tr>
            </tbody>
          </table>

          <h3><FileJson size={12} style={{ verticalAlign: "-2px" }} /> Full JSON config</h3>
          <pre>{`{
  "params": {
    "numVans": 2,
    "avgSpeedKmh": 62,
    "roadFactor": 1.32,
    "costPerKmThb": 28,
    "excessLinePct": 0.8,
    "replenishTargetPct": 0.6,
    ...
  },
  "branches": [
    { "code": "SNB-B001",
      "name": "SNB Mueang Khon Kaen Service Branch 001",
      "district": "Mueang Khon Kaen",
      "lat": 16.4322, "lng": 102.8236,
      "cashCapacity": 22000000,
      "minThreshold": 3300000,
      "openingCash": 12000000,
      "predictedInflow": 11130000,
      "predictedOutflow": 3300000 }
  ]
}`}</pre>
          <p style={{ color: "var(--muted)" }}>
            Exported files re-import losslessly. Config is auto-saved to your browser.
          </p>
        </div>
      </div>
    </div>
  );
}
