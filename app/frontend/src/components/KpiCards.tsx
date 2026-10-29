import { Clock, Banknote, Route, Truck, TrendingDown, Leaf } from "lucide-react";
import type { ExecMetrics } from "../types";
import { thb } from "../data/format";

export default function KpiCards({ m }: { m: ExecMetrics }) {
  return (
    <div className="kpi-grid">
      <div className="kpi hero">
        <Clock className="icon" size={20} color="#4ade80" />
        <div className="k-label">Man-hours saved / day</div>
        <div className="k-value">{m.manHoursSaved} h</div>
        <div className="k-sub">
          <span className="up">▼ {m.manHoursSavedPct}%</span> vs current route
        </div>
      </div>

      <div className="kpi cash">
        <Banknote className="icon" size={20} color="#38bdf8" />
        <div className="k-label">Idle cash reduction</div>
        <div className="k-value">{thb(m.idleCashReductionThb)}</div>
        <div className="k-sub">
          <span className="up">▼ {m.idleCashReductionPct}%</span> vault cash freed
        </div>
      </div>

      <div className="kpi">
        <Route className="icon" size={20} color="#38bdf8" />
        <div className="k-label">Distance reduced</div>
        <div className="k-value">{m.distanceSavedKm} km</div>
        <div className="k-sub">
          <span className="up">▼ {m.distanceSavedPct}%</span> per planning cycle
        </div>
      </div>

      <div className="kpi">
        <Banknote className="icon" size={20} color="#f59e0b" />
        <div className="k-label">Transport cost saved</div>
        <div className="k-value">{thb(m.fuelCostSavedThb)}</div>
        <div className="k-sub">fuel · crew · carrier / day</div>
      </div>

      <div className="kpi">
        <Truck className="icon" size={20} color="#a78bfa" />
        <div className="k-label">Fleet utilization</div>
        <div className="k-value">
          {m.branchesServed}/{m.branchesTotal}
        </div>
        <div className="k-sub">branches served this cycle</div>
      </div>

      <div className="kpi">
        <TrendingDown className="icon" size={20} color="#4ade80" />
        <div className="k-label">On-time SLA</div>
        <div className="k-value">{m.onTimePct}%</div>
        <div className="k-sub">within branch time windows</div>
      </div>

      <div className="kpi">
        <Banknote className="icon" size={20} color="#38bdf8" />
        <div className="k-label">Idle cash before → after</div>
        <div className="k-value">{thb(m.idleCashAfterThb)}</div>
        <div className="k-sub">from {thb(m.idleCashBeforeThb)} idle</div>
      </div>

      <div className="kpi">
        <Leaf className="icon" size={20} color="#4ade80" />
        <div className="k-label">CO₂ avoided</div>
        <div className="k-value">{m.co2SavedKg} kg</div>
        <div className="k-sub">lower armored-fleet mileage</div>
      </div>
    </div>
  );
}
