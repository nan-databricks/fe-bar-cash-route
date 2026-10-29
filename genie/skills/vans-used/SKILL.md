---
name: vans-used
description: Count CIT vans (vehicles) used on a service date for BASELINE and/or OPTIMIZED plans. Use for "how many vans", "vehicles_used", "fleet utilisation".
---

# Vans used

Fleet size is 30 vans across 3 depots.

## Steps

1. Historical fixed cycle: `SUM(vehicles_used)` from `gold_baseline_daily` (grain is depot × day; last day 2026-09-30).
2. Plan comparison on 2026-10-01: `vehicles_used` from `gold_route_summary` per `plan_type`, or `COUNT(DISTINCT vehicle_id)` from `gold_routes`.
3. If ML tables are missing, report only the 2026-09-30 baseline and say optimized van count will appear after the route job.

## Answer shape

- Baseline **2026-09-30**: **V** vans, cost THB C (sum across depots).
- Optimized **2026-10-01** (if present): **V2** vans.

Do not add depot-level van counts unless asked; `gold_baseline_daily.vehicles_used` is already per depot so always SUM.
