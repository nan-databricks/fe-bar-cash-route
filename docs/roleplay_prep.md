# Role-play prep — business and technical objections

## Personas

| Persona | Cares about | Pitch altitude |
|---|---|---|
| CFO | Cost of CIT + cost of idle cash + reputational cash-outs | THB, annualised, risk |
| Head of Cash Ops | SLA, van hours, payday chaos, driver change management | Today’s plan vs yesterday’s radio |
| CIO / CISO | PDPA, who sees custodian phone numbers, audit | UC mask/row filter, no real customer data in *this* build |
| Data platform lead | Pipeline quality, serving, Lakebase vs warehouse, lock-in | Contract tables, CDF, serverless job |

## Discovery questions (ask if the AI persona gives you room)

- How do you decide which ATM is visited tomorrow — calendar, branch call, or telemetry?
- What is a cash-out worth (SLA penalty, brand, cash in the van to recover)?
- Who is allowed to change a route after 07:00, and where is that logged today?
- Do CIT crews already have handhelds, or is the plan still paper / radio?

---

## Business objections

**“31% looks like a vendor slide.”**  
It is a **synthetic** like-for-like on one service date: same nodes, same vans, fixed cycle vs CVRP-TW. The pilot metric is **≥20%** cost or km on one depot for 30 days, with cash-outs not worse. I will not claim a named bank’s result.

**“We can’t strand customers at empty ATMs to save diesel.”**  
The objective is the opposite. CRITICAL nodes get a high drop penalty so the solver almost always visits them. P80 replenishment over-fills slightly so we trade a bit of idle cash for SLA. Baseline in the demo still has 19 cash-out-risk nodes; optimized has 2.

**“Idle cash reduction will never hit the P&amp;L.”**  
It hits **cost of funds** and vault capacity. Even a partial reduction (demo: ~THB 42M on the estate snapshot) frees cassette capacity for payday. We report it as a Cash Ops KPI, not as booked revenue.

**“Drivers will ignore the app.”**  
Dispatchers keep a veto: Lakebase `dispatch_overrides` with a reason. Success criterion is **80% accept**, not 100% automation. No autonomous cash movement.

**“Time to value?”**  
This build is the production *shape*: volume → Lakeflow → UC → model → routes → Lakebase → app. A real bank swaps the synthetic generator for their ATM switch / vault files under the same silver schema. Pilot scope is one cash centre, not a core-banking replacement.

**“Why not a routing vendor / Google OR in a VM?”**  
You still need governed demand, PII, audit, and a control room. The solver is the cheap part. Databricks is where forecast, governance, serving, and dispatch state share a catalog.

---

## Technical objections

**“Cash telemetry is sensitive.”**  
Custodian name and phone are **column-masked**. Historic trips are **row-filtered by depot**. Gold is what the app SP can SELECT. This repo contains **only synthetic** SNB data — no real branch codes.

**“Batch forecast isn’t real-time.”**  
CIT is a **morning plan** problem, not a 50ms fraud problem. Nightly solve + on-demand Re-forecast (serving endpoint, scale-to-zero) covers payday exceptions. Intra-day re-solve is a job parameter, not a new system.

**“Global LightGBM will miss local spikes.”**  
Node type is categorical; lags and holiday/payday flags are in gold features. If a depot’s WAPE gaps, we add a depot feature or a hierarchical model without changing the serving contract (`pred_net_outflow_thb`, `pred_p80_thb`).

**“OR-Tools is not a commercial solver.”**  
20–30s Guided Local Search per depot is enough for ~60–120 orders. Production can warm-start and raise the limit. We keep OR-Tools because the route table contract is stable if the solver changes.

**“Why Lakebase if we have a warehouse?”**  
Warehouse is analytical. Dispatchers **write** overrides and need indexed point reads on today’s stops. Lakebase Autoscaling syncs gold via CDF and holds `dispatch_overrides`. The app does not become the source of truth for routes.

**“Genie will hallucinate balances.”**  
Space is **gold-only**, with joins and benchmark questions committed as text. Agent mode can run SQL; we do not let it approve a route. Humans confirm in the app.

**“Snowflake / Fabric already has the lake.”**  
The integrated path here is pipeline expectations + UC model + serving + Lakebase writeback + Genie + App in one identity plane. I’m not asking them to rip out ingestion overnight; I’m asking for the control room on this contract.

**“Serverless cost.”**  
Jobs and the endpoint scale to zero. CIT is one daily solve plus a few forecast clicks. Cost of **one cash-out** or a wasted van-day dominates the warehouse bill; we can show job run DBU in the evidence folder after the e2e run.

**“Lakebase maturity.”**  
Synced tables from CDF, SNAPSHOT keys in the contract, app SP grants. If Autoscaling is blocked, the fallback is warehouse reads + a Delta table for overrides — same API, worse latency. We prefer Lakebase because writeback is in the FE Bar path and in the ops story.

---

## Proof points → files

| Claim | Evidence (text) |
|---|---|
| Pipeline ran with expectations | `evidence/data_pipeline_events.txt` |
| Table counts | `evidence/data_table_counts.txt` |
| Mask / tags | `evidence/data_governance.txt` |
| WAPE vs naive | `evidence/ml_train_metrics.txt` |
| Endpoint sample | `evidence/ml_endpoint_response.txt` |
| Baseline vs optimized KPIs | `evidence/ml_route_summary.txt` |
| App health | `evidence/app_health.txt` |
| Genie Q&amp;A | `evidence/genie_benchmarks.txt` |
| Lakebase row counts | `evidence/lakebase_counts.txt` |
| Decisions | `docs/decisions.md` |
