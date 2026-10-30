# FE Bar submission form: draft answers

Draft answers for every field on the **Build** tab, plus the role-play tab. Paste after the integrator has replaced every `{{...}}` token with real values from `evidence/` (see `deck/PLACEHOLDERS.md`).

**Attestation checkbox and typed full name: Nan to complete. Do not fill these in on Nan's behalf.**

---

## Customer name

Siam Northeast Bank (SNB). This is a fictional regional bank; all data is synthetic.

## Industry / vertical

Financial Services: retail banking, cash logistics (cash-in-transit and ATM/RCM replenishment).

## What is the business challenge you are solving? *(required)*

Siam Northeast Bank, a fictional regional bank in Khon Kaen, Northeast Thailand, serves 159 branches and 520 cash machines (400 ATMs and 120 cash-recycling machines) from 3 cash centres with 30 armoured cash-in-transit (CIT) vans. Every node is replenished on a fixed 5-day cycle, regardless of demand. That causes three daily losses:

1. **Wasted CIT cost**: vans and armed crews visit machines that are still mostly full, on static routes that overrun bank opening hours.
2. **Cash-outs**: payday and public-holiday demand empties ATMs before the next scheduled visit, which costs fee income, creates complaints and damages trust in rural districts.
3. **Idle cash**: cassettes and branch vaults are overstocked "just in case", tying up non-earning float.

Cash Operations plans from yesterday's spreadsheets and cannot answer "which machines run dry by Friday, and which van should go?". The buyer's KPIs are CIT cost per day (THB), idle cash (THB), cash-out incidents, route km and time-window SLA %.

## How does your Databricks solution address this challenge? *(required)*

One integrated, governed data journey on Databricks, deployed as a single Databricks Asset Bundle and run end to end by one job (`snb_cash_ops_e2e`) on serverless compute:

1. **Lakeflow Spark Declarative Pipelines** (`snb_cash_ops_pipeline`): Auto Loader ingests 8 synthetic raw feeds (depots, vans, branches, machines, calendar, daily machine and branch cash, historical CIT trips) from a Unity Catalog volume into bronze. Typed silver tables enforce data-quality expectations (drop null keys and negative cash; warn on coordinates outside Thailand). Gold tables provide unified node cash flow, demand features, node status and baseline KPIs.
2. **Unity Catalog** governs everything: layer, domain and PII tags; a column mask on CIT custodian name and phone; a row filter so each cash centre's dispatchers see only their own trips; gold-only grants; and lineage from raw file to app.
3. **ML**: a global LightGBM model (point forecast plus a P80 quantile) predicts daily net cash demand for all 679 nodes. It is tracked in MLflow, registered in Unity Catalog as `cash_demand_forecast@champion` and served on the Model Serving endpoint `snb-cash-forecast`. Holdout WAPE is 25% against 39% for a naive baseline.
4. **Decisioning**: forecasts become replenishment orders (deliver or pickup, amount, priority, time window). An OR-Tools capacitated vehicle routing solver with time windows (CVRP-TW) builds each depot's routes, and writes the fixed-cycle baseline in the same schema for comparison.
5. **Lakebase Autoscaling** (`snb-cash-ops`): UC synced tables serve route stops and node status to the app with millisecond reads. A writable Postgres table `dispatch_overrides` records dispatcher decisions (skip, add, resequence, emergency) with reason and author.
6. **Genie space "SNB Cash Ops Assistant"** in agent mode lets Cash Ops ask plain-language questions over the governed gold tables, for example "Which ATMs will cash out in the next 3 days?". Masks and row filters still apply.
7. **Databricks App `snb-cash-route`** (React + FastAPI) is the control room: a map of optimized vs baseline routes, KPI cards, the order list, a live re-forecast button that calls the serving endpoint, the dispatch-override form writing to Lakebase, and embedded Genie chat.

Each stage consumes the previous stage's governed output; nothing is copied out of Unity Catalog.

## What AI tools did you use, and what was your workflow? What decisions and trade-offs did you make?

**Tools and workflow.** Built in Cursor using a team of parallel AI agents coordinated by a lead agent. I first froze a contract, `contract/naming.md` (every resource name) and `contract/tables.yaml` (every table and column, plus the app API), so agents could build in parallel without integration drift. Specialist agents each owned one folder: data (generator, Lakeflow, governance), ML (forecast, serving, orders, optimizer), Lakebase, Genie, app, and narrative. Every agent committed text evidence of its run to `evidence/`. I used the Databricks CLI (profile `nan-demo`) and Asset Bundles for deployment, and reviewed and directed the industry framing, design decisions and narrative myself. *(Nan: adjust to describe your own prompting and review loop.)*

**Key decisions and trade-offs** (full detail in `docs/decisions.md`):
- **Declarative pipelines over notebooks** for ingestion: expectations, event log and lineage come built in. Imperative steps (ML, solver) remain notebook tasks in the same job.
- **One global LightGBM over 679 per-node models**: it shares payday and holiday signal and can forecast new machines, at the cost of less per-node tuning.
- **P80 quantile for replenishment**: a cash-out costs more than carrying slightly more cash, so we accept some idle float on purpose.
- **OR-Tools CVRP-TW with a 25-second limit per depot**: open source and explainable, with a good-enough morning plan. It is not provably optimal; a commercial solver is an option at larger scale.
- **Lakebase synced tables plus a writable overrides table**, instead of the app querying the SQL warehouse: millisecond reads and a transactional write path, with snapshot freshness per job run.
- **Genie agent mode instead of a custom agent**: governed by UC and fast to value, with less custom tool control.
- **Serverless everywhere**: scale-to-zero suits a once-a-day plan; the cost is cold starts.
- **Synthetic data**: no real customer data, with a deliberately rigid baseline. The results are indicative and get validated in a pilot.

## What are the business outcomes and impact?

On the synthetic plan day (2026-10-01), against the fixed 5-day cycle for the same estate:

- **CIT cost per day:** THB 75,400 → THB 69,550 (**−8%**), about **THB 1.5M a year**
- **Vans dispatched:** 11 → 13; **route km −23%**
- **Cash-out risk nodes:** 64 → 0
- **Idle cash released:** THB 43M
- **Time-window SLA:** 100%
- **Forecast accuracy:** WAPE 25% vs 39% naive

For the executive sponsor, that means lower cost-to-serve, less non-earning float and protected fee income. For the Head of Cash Operations, it means a ready plan each morning, an auditable override path and plain-language answers. All figures are synthetic-data demo results, not customer results. The proposed next step is a 30-day pilot in one cash centre, with success defined as ≥ 20% lower CIT cost or km, cash-outs not higher, and ≥ 80% dispatcher acceptance.

## GitHub repo link *(required)*

https://github.com/nan-databricks/fe-bar-cash-route (must be public, or connected through the form if the repo is in a private EMU org).

## Presentation deck *(required; .pdf/.txt/.md)*

Upload `deck/deck.pdf` (source: `deck/deck.md`). Rebuild after filling KPIs with `bash deck/build_pdf.sh`.

## Local repo folder *(required)*

`/Users/nan.chulpaibul/Documents/demo/Q42026/fe-bar-cash-route`

Before selecting it: confirm `evidence/` is populated, no `{{...}}` tokens remain outside `deck/PLACEHOLDERS.md`, and a repo-wide search for real bank names, logos or branch codes returns nothing.

## Conversation ID *(optional)*

Cursor agent session: `e1a675d3-db0b-4072-9134-25bc32a69993`. *(Nan: confirm this is the parent build session.)*

## AI Customer Challenge build checkbox

**Leave unchecked.** SNB is an original fictional customer, not one of the challenge customers (NorthPeak Retail, Meridian Bank, Cedar Health, Volta Industrial, Streamline Telco, Nimbus, Brightwave, The Benefits Agency). The build nevertheless includes net-new work for all three challenge items: a Lakeflow pipeline, a trained and served ML model, and a Genie agent.

## Attestation checkbox + typed full name *(required)*

**Nan to complete.** The attestation confirms the work is your own, was not generated from go/solution-builder, and that you understand the consequences of misrepresentation.

## Optional: request a human validator

Not requested by default.

---

## Role-play tab (Yoodli)

- **Demo recording link (if needed):** {{DEMO_VIDEO_URL}}
- Prep material: `docs/roleplay_prep.md` (personas, objections, proof points) and `docs/demo_script.md` (timed click path).
- The form notes "Pass your build first, then submit your role-play".
