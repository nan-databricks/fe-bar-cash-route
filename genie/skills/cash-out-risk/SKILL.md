---
name: cash-out-risk
description: List SNB branches, ATMs, and RCMs that will cash out (run out of cash) within N days if not replenished. Use for "which nodes cash out in 3 days", "run-out risk", "days to cash-out", "CRITICAL nodes".
---

# Cash-out risk

Default horizon is **3 days**. Snapshot date is **2026-09-30**. Plan date is **2026-10-01**.

## Steps

1. If `gold_replenishment_orders` exists, query it for `service_date = DATE '2026-10-01'` and `days_to_cashout <= N`.
2. Otherwise compute from `gold_node_status`:
   `days_to_cashout = current_cash_thb / NULLIF(avg_daily_outflow_28d, 0)`
   Keep rows with `avg_daily_outflow_28d > 0` and `days_to_cashout <= N`.
3. Join `gold_cash_nodes` for `node_name`, `node_type`, `district`.
4. Sort by `days_to_cashout` ascending. Cap the table at 25 rows plus a total count.

## Answer shape

**N nodes** would cash out within **3 days** as of 2026-09-30 (or from replenishment orders on 2026-10-01).

| node_id | node_type | node_name | depot_id | days_to_cashout | priority |
|---|---|---|---|---|---|

One sentence on the busiest depot. Do not invent priorities if the fallback path has none.
