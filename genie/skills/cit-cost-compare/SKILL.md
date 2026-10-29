---
name: cit-cost-compare
description: Compare SNB CIT (cash-in-transit) cost of the demand-driven OPTIMIZED plan versus the fixed-cycle BASELINE. Use for "optimized vs baseline", "CIT cost", "km saved", "SLA", "idle cash".
---

# CIT cost optimized vs baseline

Service date for the ML plan is **2026-10-01**.

## Steps

1. If `gold_route_summary` exists, `SELECT * WHERE service_date = DATE '2026-10-01'` for both `plan_type` values.
2. If it does not exist, say the ML route tables are not ready. Do **not** fabricate an optimized cost. Optionally show historical `gold_baseline_daily` for 2026-09-30 only, labelled as last cycle day, not the 1 Oct plan.
3. Compute deltas: cost, vehicles_used, km, cashout_risk_nodes, idle_cash_thb, sla_pct.

## Answer shape

For **2026-10-01**:

| plan_type | cost_thb | vehicles_used | km | cashout_risk_nodes | idle_cash_thb | sla_pct |
|---|---|---|---|---|---|---|

Lead with: "Optimized CIT cost is THB X vs baseline THB Y (Z% lower)."
