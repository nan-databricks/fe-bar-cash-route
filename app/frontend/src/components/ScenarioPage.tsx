import { useMemo, useState } from "react";
import { Play, Lightbulb, Check } from "lucide-react";
import type { AppConfig, Branch, RoutePlan } from "../types";
import { thb } from "../data/format";
import {
  runScenario,
  SCENARIO_PRESETS,
  DEFAULT_ASSUMPTIONS,
  type ScenarioAssumptions,
  type SimResultRow,
} from "../data/scenario";
import MapView from "./MapView";

function fmtValue(row: SimResultRow): string {
  switch (row.unit) {
    case "km":
      return `${row.scenario.toLocaleString(undefined, { maximumFractionDigits: 1 })} km`;
    case "hrs":
      return `${row.scenario.toLocaleString(undefined, { maximumFractionDigits: 1 })} hrs`;
    case "thb":
      return thb(row.scenario);
    case "pct":
      return `${row.scenario}%`;
    default:
      return String(row.scenario);
  }
}

function DeltaTag({ row }: { row: SimResultRow }) {
  if (row.unit === "pct") {
    const good = row.deltaPct >= 0;
    if (row.deltaPct === 0) return <span className="sc-delta flat">(=)</span>;
    return (
      <span className={`sc-delta ${good ? "good" : "bad"}`}>
        ({row.deltaPct > 0 ? "+" : ""}
        {row.deltaPct}pp)
      </span>
    );
  }
  if (row.deltaPct === 0) return <span className="sc-delta flat">(=)</span>;
  const worse = row.higherIsWorse ? row.deltaPct > 0 : row.deltaPct < 0;
  return (
    <span className={`sc-delta ${worse ? "bad" : "good"}`}>
      ({row.deltaPct > 0 ? "+" : ""}
      {row.deltaPct}%)
    </span>
  );
}

function barPct(row: SimResultRow): number {
  if (row.unit === "pct") return Math.min(100, row.scenario);
  const max = Math.max(row.base, row.scenario) || 1;
  return Math.min(100, (row.scenario / max) * 100);
}

export default function ScenarioPage({
  config,
  onApplyScenario,
}: {
  config: AppConfig;
  onApplyScenario: (c: AppConfig) => void;
}) {
  const [presetId, setPresetId] = useState("demand10");
  const [assumptions, setAssumptions] = useState<ScenarioAssumptions>(DEFAULT_ASSUMPTIONS);
  const [applied, setApplied] = useState<ScenarioAssumptions | null>(DEFAULT_ASSUMPTIONS);
  const [appliedPreset, setAppliedPreset] = useState("demand10");

  const setPreset = (id: string) => {
    setPresetId(id);
    const preset = SCENARIO_PRESETS.find((p) => p.id === id);
    if (preset && Object.keys(preset.assumptions).length) {
      setAssumptions((a) => ({ ...a, ...preset.assumptions }));
    }
  };

  const setField = (key: keyof ScenarioAssumptions, value: number) => {
    setPresetId("custom");
    setAssumptions((a) => ({ ...a, [key]: value }));
  };

  const result = useMemo(
    () => (applied ? runScenario(config, applied, appliedPreset) : null),
    [config, applied, appliedPreset]
  );

  const run = () => {
    setApplied({ ...assumptions });
    setAppliedPreset(presetId);
  };

  return (
    <div className="scenario-page">
      <div className="panel sc-control">
        <div className="sc-control-field">
          <label>Scenario Type</label>
          <select value={presetId} onChange={(e) => setPreset(e.target.value)} className="select-inline">
            {SCENARIO_PRESETS.map((p) => (
              <option key={p.id} value={p.id}>
                {p.label}
              </option>
            ))}
          </select>
        </div>
        <div className="sc-control-field">
          <label>Date</label>
          <input type="text" readOnly value={config.params.planDate} className="select-inline" />
        </div>
        <div style={{ flex: 1 }} />
        <button type="button" className="btn primary" onClick={run}>
          <Play size={15} /> Run Simulation
        </button>
      </div>

      <div className="scenario-grid">
        <div className="panel">
          <div className="panel-head">
            <h2>Scenario Assumptions</h2>
          </div>
          <div className="panel-body sc-assumptions">
            <Sc label="Demand Change" suffix="%" value={assumptions.demandChangePct} onChange={(v) => setField("demandChangePct", v)} signed />
            <Sc label="Cash In Change" suffix="%" value={assumptions.cashInChangePct} onChange={(v) => setField("cashInChangePct", v)} signed />
            <Sc label="Available Trucks" value={assumptions.availableTrucks} onChange={(v) => setField("availableTrucks", v)} />
            <Sc label="Max Route Duration" suffix=" hrs" value={assumptions.maxRouteDurationH} onChange={(v) => setField("maxRouteDurationH", v)} />
            <Sc label="Truck Capacity" value={assumptions.truckCapacityThb} onChange={(v) => setField("truckCapacityThb", v)} money />
          </div>
        </div>

        <div className="panel">
          <div className="panel-head">
            <h2>Simulation Results</h2>
            <span className="hint">vs Base Plan</span>
          </div>
          <div className="panel-body sc-results">
            {result?.rows.map((row) => (
              <div className="sc-result-row" key={row.key}>
                <span className="sc-result-label">{row.label}</span>
                <div className="sc-result-track">
                  <div
                    className="sc-result-fill"
                    style={{ width: `${barPct(row)}%`, background: row.unit === "pct" ? "#22c55e" : "#2563eb" }}
                  />
                </div>
                <span className="sc-result-value">
                  {fmtValue(row)} <DeltaTag row={row} />
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="panel sc-map-panel">
          <div className="panel-head">
            <h2>Map Preview</h2>
            <span className="hint">Delivery · Pickup · Both · Emergency</span>
          </div>
          <div className="sc-map">
            {result && (
              <ScenarioMapPreview
                key={`${appliedPreset}-${result.scenario.optimized.vehiclesUsed}`}
                branches={result.scenario.branches}
                optimized={result.scenario.optimized}
                original={result.scenario.original}
              />
            )}
          </div>
        </div>
      </div>

      {result && (
        <div className="panel sc-reco">
          <div className="sc-reco-head">
            <Lightbulb size={18} color="#f59e0b" />
            <h2>Recommendation</h2>
          </div>
          <div className="sc-reco-body">
            {result.additionalTrucks > 0 ? (
              <>
                <p>
                  Under this scenario, you need <strong>{result.additionalTrucks} additional truck{result.additionalTrucks > 1 ? "s" : ""}</strong>{" "}
                  to maintain SLA &gt; 90% (longest route reaches {result.longestRouteH} hrs vs {assumptions.maxRouteDurationH} hr cap).
                </p>
                <p>
                  Or adjust max route duration to <strong>{result.recommendedDurationH} hrs</strong> to keep the same fleet of{" "}
                  {result.vehiclesRequired} vehicle{result.vehiclesRequired > 1 ? "s" : ""}.
                </p>
              </>
            ) : (
              <p>
                The current fleet of <strong>{result.vehiclesRequired} vehicle{result.vehiclesRequired > 1 ? "s" : ""}</strong> absorbs this
                scenario within the {assumptions.maxRouteDurationH} hr shift cap — projected SLA {result.slaScenario}%.
                {!result.feasible && " Note: required vehicles exceed available trucks."}
              </p>
            )}
          </div>
          <button type="button" className="btn primary sc-apply" onClick={() => onApplyScenario(result.scenarioConfig)}>
            <Check size={15} /> Apply Scenario
          </button>
        </div>
      )}
    </div>
  );
}

function Sc({
  label,
  value,
  onChange,
  suffix,
  signed,
  money,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  suffix?: string;
  signed?: boolean;
  money?: boolean;
}) {
  const display = money ? Math.round(value / 1_000_000) : value;
  return (
    <div className="sc-assume-row">
      <span className="sc-assume-label">{label}</span>
      <span className="sc-assume-value">
        <input
          type="number"
          value={display}
          onChange={(e) => onChange(money ? Number(e.target.value) * 1_000_000 : Number(e.target.value))}
          className="sc-input"
        />
        <span className={`sc-assume-suffix ${signed && value > 0 ? "pos" : signed && value < 0 ? "neg" : ""}`}>
          {money ? "M THB" : suffix}
        </span>
      </span>
    </div>
  );
}

function ScenarioMapPreview({
  branches,
  optimized,
  original,
}: {
  branches: Branch[];
  optimized: RoutePlan;
  original: RoutePlan;
}) {
  const [showOptimized, setShowOptimized] = useState(true);
  const [showOriginal, setShowOriginal] = useState(false);
  return (
    <MapView
      branches={branches}
      optimized={optimized}
      original={original}
      showOptimized={showOptimized}
      showOriginal={showOriginal}
      onToggleOptimized={() => {
        setShowOptimized(true);
        setShowOriginal(false);
      }}
      onToggleOriginal={() => {
        setShowOptimized(false);
        setShowOriginal(true);
      }}
      compareRouteLabel="Actual"
    />
  );
}
