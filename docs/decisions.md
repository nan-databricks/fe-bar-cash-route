# Decisions and trade-offs

Siam Northeast Bank (SNB) is fictional and all data is synthetic. This page records what we chose, why, what it costs us, and what we would change for a real bank.

## Summary

| # | Decision | Why | Trade-off we accepted |
|---|---|---|---|
| 1 | CIT route optimization for a regional bank, not a generic "ops copilot" | Buyer KPIs (cost/day, idle cash, cash-outs, km, SLA) can be measured on one plan day | Narrower story; one use case only |
| 2 | Synthetic 18-month daily panel with a deliberately rigid 5-day cycle | No real customer data; gives the optimizer an honest, reproducible baseline | Demand patterns are cleaner than reality, so results are indicative |
| 3 | Lakeflow Spark Declarative Pipelines for ingest, notebooks for imperative steps | Expectations, event log, lineage and incremental Auto Loader come for free | Generation, governance, ML and the solver stay as notebook tasks |
| 4 | One global LightGBM, not one model per node | Shares payday/holiday signal across 679 nodes, cold-starts new ATMs, one endpoint | Less per-node tuning |
| 5 | P80 quantile drives replenishment size | A cash-out costs more than carrying a little extra cash | Some idle cash is kept on purpose |
| 6 | OR-Tools CVRP-TW per depot, 25 s time limit | Open source, explainable, good-enough morning plan in seconds | Not provably optimal |
| 7 | Lakebase synced tables + writable overrides, not app-to-warehouse | Low-latency point reads and a real write path for dispatchers | Snapshot sync, so freshness is per job run |
| 8 | Genie space with agent mode, not a custom tool-calling agent | Governed by UC, no prompt plumbing, fast to value for Cash Ops | Less control over custom tools and flows |
| 9 | Serverless everywhere | No cluster operations, scale-to-zero for a once-a-day workload | Cold starts; per-DBU price at very high volume |
| 10 | Row filter by depot, column mask on custodian PII | Mirrors how cash centres are actually organised; custodians are personal data under Thailand's PDPA | Filter falls back to a governed view if the pipeline-managed table rejects it |
| 11 | One Databricks Asset Bundle, one end-to-end job | Whole journey reproducible in two commands | App is deployed with `databricks apps deploy`, outside the bundle |

## 1. Problem selection

Cash-in-transit (CIT) logistics is a concrete, industry-specific banking problem with a clear owner (Head of Cash Operations), a clear funder (CFO/COO), and costs that show up daily: armed vans, crew hours, idle float, and cash-outs. That makes it easier to quantify than "improve operations".

## 2. Synthetic data design

- Estate: 3 cash centres, 30 vans, 159 branches, 520 machines (400 ATM + 120 RCM) in Khon Kaen province. Branches are random points around Khon Kaen city spread across seven district names, assigned to the nearest cash centre; machines sit near a branch at synthetic retail and mall sites. IDs are synthetic (`SNB-B001` and so on); no real branch codes or names. Fixed seed (42026), so every run reproduces the same estate.
- History: 2025-04-01 to 2026-09-30, daily. Demand has weekend (+10%), payday (day 25 to month-start, +35%), Thai public holiday (+18%), seasonal and per-node scale effects, plus noise.
- Baseline: every node is replenished on a fixed 5-day offset, and the historical CIT trips use 22–28 vans per day. Some nodes are seeded close to empty on the last day so the "cash-out risk" KPI is meaningful.
- Trade-off: synthetic data is cleaner than real ATM journals (no switch outages, no denomination mix, no reconciliation breaks). Savings are therefore indicative, and the pilot is where they are validated.

## 3. Lakeflow Spark Declarative Pipelines vs notebooks

We chose a declarative pipeline (`snb_cash_ops_pipeline`) for raw → bronze → silver → gold because:
- Auto Loader ingests new files incrementally without bookkeeping.
- `expect_or_drop` rules (null keys, negative cash) and `expect` warnings (coordinates outside Thailand) are recorded in the event log as text evidence.
- Lineage and dependency ordering come from the code, not from a scheduler config.

Imperative steps (data generation, governance DDL, MLflow training, serving, scoring, OR-Tools) stay as notebook tasks in the same job, because they call SDKs and libraries rather than transform tables.

In production we would add quarantine tables for rows that fail expectations rather than only dropping them.

## 4. Forecasting: global LightGBM

- One model across branches, ATMs and RCMs, with `node_type` as a categorical feature and lag/rolling/calendar features from `gold_demand_features`.
- Time-based holdout (train before 2026-08-01, validate Aug–Sep 2026) and a published lag-7 / rolling-28 naive baseline, so the model has to beat something real. Metric: WAPE (robust for low-volume nodes), plus MAPE.
- Per-node models were rejected: 679 sparse series, 679 artefacts, and no way to forecast a new machine.
- If depot-level WAPE diverges on real data, the next step is a hierarchical or depot-feature model behind the same serving contract (`pred_net_outflow_thb`, `pred_p80_thb`).

## 5. P80 quantile for safety stock

Replenishment amounts use the P80 forecast (a second LightGBM with a quantile objective), not the mean. Under-filling before payday causes a cash-out and an emergency run; over-filling costs only the carry cost of a few cassettes. P80 is a deliberate, explainable risk setting that Cash Ops can tune (P70–P90) per node type once real cost-of-cash-out figures are known.

## 6. Route optimization: OR-Tools CVRP-TW

- Capacitated vehicle routing with time windows, solved per depot: van cash capacity, bank opening hours as time windows, a 07:00–18:00 shift, and service time per stop.
- First solution from cheapest-arc, improved with Guided Local Search under a **25-second time limit per depot**.
- CRITICAL orders carry a very high drop penalty, so in practice SLA behaves as a constraint rather than a soft cost.
- Cost model for comparison: distance cost plus THB 2,500 fixed per van-day; road distance = straight-line × 1.3 (no live traffic).
- The baseline is written with the same schema (`plan_type = BASELINE | OPTIMIZED`), so the app toggle is just a filter.
- A commercial solver (Gurobi, Hexaly) could add a few percent at large scale or support intraday dynamic re-plans. We kept OR-Tools for transparency and zero licence cost; the route-table contract would not change if the solver did.

## 7. Lakebase synced tables vs querying the warehouse from the app

- `lb_route_stops` and `lb_node_status` are UC synced tables into Lakebase Autoscaling project `snb-cash-ops`. The app gets indexed point reads in milliseconds.
- `public.dispatch_overrides` is a normal writable Postgres table: dispatchers record SKIP / ADD / RESEQUENCE / EMERGENCY with a reason and author. That is operational state; it does not belong in an analytical warehouse.
- Alternative considered: the app reads the SQL warehouse directly and writes overrides to a Delta table. Simpler, but higher latency per click and no transactional write path. We kept this as the fallback if Lakebase is unavailable.
- Trade-off: synced tables use SNAPSHOT mode, so they refresh when the job runs. Continuous sync from the Delta change data feed is the production upgrade.

## 8. Genie agent mode vs a custom agent

The Genie space "SNB Cash Ops Assistant" covers the gold tables, with instructions, join definitions, sample SQL and benchmark questions. Agent mode handles multi-step questions ("which nodes cash out by Friday, and which van covers them?").

We did not build a custom LangGraph/Agent Framework agent. Genie inherits UC permissions (masks and row filters still apply), needs no prompt plumbing, and Cash Ops can use it on day one. We would add a custom agent only for actions Genie should not take (for example, proposing overrides), and even then a human would confirm in the app.

## 9. Serverless everywhere

Jobs, the pipeline, notebooks, the SQL warehouse and Model Serving are all serverless, and the endpoint can scale to zero. CIT planning is a once-a-day batch plus a handful of re-forecasts, so idle cost dominates and scale-to-zero wins. Trade-off: cold starts of tens of seconds on the endpoint and job tasks, which is acceptable for a morning plan.

## 10. Governance design

- **Column mask** `snb_mask_custodian` on `custodian_name` and `custodian_phone`: only `snb_pii_readers` (and admins in the demo) see clear text; everyone else sees `***`.
- **Row filter** `snb_depot_filter` on `silver_cit_trips` by `depot_id`: a dispatcher in one cash centre sees only their trips. If the pipeline-managed table rejects the filter, a governed view `silver_cit_trips_governed` is created instead.
- **Tags** for layer, domain and PII classification; **grants** expose gold only; bronze/silver stay restricted.
- In production the demo group `snb_ops_kkn_c` maps to SCIM-synced IdP groups per cash centre.

## 11. Delivery: one bundle, one job

`databricks bundle deploy` creates the pipeline and the job; `databricks bundle run snb_cash_ops_e2e` runs raw → app-ready. The app is deployed with `databricks apps deploy` because its source sync and its resources (Lakebase, serving endpoint, Genie space) are bound after those exist.

## What we would do differently in production

1. Replace the synthetic generator with real ATM switch, vault and CIT handheld feeds via Lakeflow Connect or file drops, under the **same silver contract**.
2. Quarantine failed records; add data-quality SLAs per source.
3. Model monitoring (Lakehouse Monitoring on inference tables), drift alerts, a champion/challenger alias flow.
4. Real road network travel times (OSRM or a maps API), traffic by hour, and a warm-start from yesterday's routes; intraday re-solve on payday.
5. Denomination mix and cassette-level planning; CIT vendor SLA penalties in the objective.
6. Continuous Lakebase sync from the change data feed; dual control (maker-checker) on overrides; PDPA retention on custodian PII.
7. CI/CD for the bundle across dev/staging/prod with service principals.
