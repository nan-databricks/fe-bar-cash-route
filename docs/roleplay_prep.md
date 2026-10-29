# Role-play prep: SNB Cash Logistics

Yoodli scores: **demo setup**, **tell-show-tell**, **value communication**, **reading the room**, **professionalism**. You face one business and one technical persona in the same session. Lead with the outcome, quantify in THB, and pitch each answer at the altitude of whoever asked.

Fill `{{...}}` with real run values before rehearsing (see `deck/PLACEHOLDERS.md`). Always say "on synthetic data" once when quoting results.

## Personas

| Persona | Cares about | Pitch altitude | Their likely first question |
|---|---|---|---|
| **CFO / COO** (business, funds it) | CIT cost, idle float, reputational cash-outs, payback | THB per year, risk, time to value | "What does this save me, and how sure are you?" |
| **Head of Cash Operations** (business, domain owner) | SLA, van hours, payday chaos, driver and dispatcher adoption | Tomorrow's plan vs today's spreadsheet and radio | "Will my dispatchers actually use this?" |
| **CIO / CISO** (technical) | PDPA, who sees custodian data, audit, integration with core banking | Controls, not features | "Where does cash data live, and who can see it?" |
| **Data platform lead / architect** (technical, lives with it) | Pipeline quality, serving latency, Lakebase vs warehouse, lock-in, run cost | Contracts, SLAs, failure modes | "What happens when a feed is late or the solver times out?" |

## 30-second opener (demo setup)

> "Siam Northeast Bank runs 520 machines and 159 branches out of 3 cash centres in Khon Kaen on a fixed 5-day cycle. That wastes van-kilometres, parks idle cash in cassettes, and still lets payday ATMs run empty. I'll show you a demand-driven plan for 1 October: on synthetic data it cuts CIT cost by 8% and cash-out risk from 64 nodes to 0. First the dispatcher's control room, then how it's governed and served, then the pilot I'd propose."

## Discovery questions (use when the persona gives you room)

**Business**
- How do you decide which machine is visited tomorrow today: calendar, branch phone call, or telemetry?
- What does one cash-out cost you: lost fees, an emergency run, complaints, regulator attention?
- What is your CIT cost per van-day, and is the fleet in-house or outsourced on a per-stop contract?
- How much cash sits in machines and vaults on an average night, and what's your cost of funds?
- Who signs off a route change after 07:00, and where is that logged today?

**Technical**
- Where do ATM switch journals, vault balances and CIT handheld data land today, and how fresh is each?
- How are cash-centre staff grouped in your identity provider (for row-level access)?
- What are your PDPA and data-residency constraints for custodian and transaction data?
- Is the cloud data platform already chosen, and what runs on it?

## Business objections

**"8% looks like a vendor slide."**
It's a like-for-like comparison on **synthetic** data for one plan day: same nodes, same vans, fixed cycle vs optimized. I'm not claiming any bank's result. That's why the ask is a 30-day pilot in one cash centre, with success at ≥ 20% lower cost or km and cash-outs no worse. Your numbers decide it, not mine.

**"We can't strand customers at empty ATMs to save diesel."**
The design does the opposite. Replenishment uses the P80 forecast, so we deliberately carry a little extra. CRITICAL nodes have a very high drop penalty, so the solver practically always visits them. Cash-out risk nodes fall from 64 to 0 in the demo.

**"Idle-cash reduction never hits the P&L."**
Agreed, it's not revenue. It shows up as cost of funds and vault and cassette capacity. We report it as a Cash Ops KPI (THB 43M released in the demo) and keep the business case on CIT operating cost: THB 1.5M a year.

**"Drivers and dispatchers will ignore the app."** (change management)
The dispatcher keeps the veto. Any stop can be skipped, added or resequenced with a reason, and that's stored in Lakebase for audit and for the next plan. The pilot success criterion is 80% acceptance, not 100% automation. Drivers still get a run sheet; nothing moves cash autonomously. We'd co-design the override reasons with your dispatch lead in week one.

**"What does it cost, and what's the time to value?"**
The platform cost is small next to one van-day: one nightly job, a scale-to-zero endpoint, and a small Lakebase instance. We can quote run cost from the job's system billing tables after the pilot's first week. Time to value: the whole stack deploys from one bundle. The pilot is about connecting your three feeds under the same silver contract, roughly 6 weeks.

**"What's the risk?"**
Low and contained. It runs in parallel with the current process in one cash centre. Humans confirm every plan, and the fixed cycle stays as a fallback. The main risk is data quality in the source feeds, which the pipeline expectations surface on day one.

**"Why not just buy a routing tool?"**
The solver is the cheap part. The value is forecasting demand per machine, governing cash and custodian data, and putting the plan, overrides and questions in one place. A routing SaaS still needs all of that fed to it, and you'd run a second security model.

## Technical objections

**"Cash data is sensitive. Who sees what?"** (security of cash data)
Everything sits in Unity Catalog. Custodian name and phone are column-masked for anyone outside the PII readers group. Historical trips are row-filtered by depot, so a dispatcher sees only their cash centre. The app's service principal reads gold only; bronze and silver are restricted. Every access is audited in system tables, and lineage shows exactly which tables feed the app. This repo contains only synthetic data.

**"This is batch. We need real time."**
CIT is a morning planning problem: vans load at the cash centre once. Nightly forecast and solve covers that. Intraday exceptions are handled by the **Re-forecast** button (real-time Model Serving) and dispatcher overrides. If you need intraday re-planning on payday, it's a second job trigger on the same tables, and the pipeline can run in continuous mode on streaming ATM events without a redesign.

**"How accurate is the solver? OR-Tools isn't a commercial solver."** (solver accuracy)
OR-Tools with Guided Local Search under a 25-second limit per depot gives a feasible, explainable plan that respects capacity, time windows and shift length. It isn't provably optimal, and I wouldn't claim it is. For a hundred or so orders per depot, the gap to optimal is typically small relative to the gain over a fixed cycle. If SNB scales to thousands of stops or wants dynamic dispatch, a commercial solver plugs into the same route tables.

**"Global LightGBM will miss local spikes."**
Node type, payday, holiday, lags and rolling means are all features, and the P80 quantile covers spikes. We measure WAPE by segment, not just overall. If one depot lags, we add a depot feature or a hierarchical model behind the same endpoint contract.

**"What happens when a feed is late or bad?"** (data quality)
Expectations drop invalid rows and record counts in the pipeline event log. In production we'd quarantine failures and alert. A late feed means the job runs on yesterday's status, and the app shows `as_of_date`.

**"Why Lakebase if we already have a warehouse?"**
The warehouse is analytical. The app needs indexed point reads on today's stops and a transactional write for overrides. Lakebase gives both in Postgres, synced from gold, under the same governance. The fallback, if needed, is warehouse reads plus a Delta overrides table: same API, higher latency.

**"Is Lakebase mature enough?"** (Lakebase maturity)
Lakebase is managed Postgres with autoscaling and scale-to-zero, and synced tables come straight from Unity Catalog. The app's dependency is narrow: two read tables and one write table behind a FastAPI layer, so the blast radius is small. The architecture doesn't depend on any preview behaviour we can't fall back from.

**"Will Genie hallucinate balances?"**
Genie generates SQL over curated gold tables with defined joins and benchmark questions, and you can always see the SQL. It inherits the user's UC permissions. It answers questions; it doesn't approve routes. Humans confirm in the app.

**"We're on Snowflake / Fabric already."** (competition)
I'm not asking you to move your lake. The difference here is one platform and one governance model across pipeline quality, model training and serving, an operational Postgres database, natural-language access and the app itself. On other stacks that's typically five products and five permission models. Lakeflow can read from where your data is today, and Delta Sharing and federation avoid a big-bang migration. Start with the pilot on this use case. (Stay factual; don't disparage competitors.)

**"Serverless will get expensive."** (cost of serverless)
This workload is one nightly run plus a few forecast calls. Serverless and scale-to-zero mean you pay for minutes, not idle clusters. Budget policies and system billing tables give per-job cost visibility. Compared with the cost of one wasted van-day or one cash-out, platform cost is a rounding error, and we'll show actual DBU cost in the pilot.

**"Lock-in?"**
Open formats throughout: Delta/Iceberg tables, MLflow models, Postgres for Lakebase, open-source OR-Tools, and a React/FastAPI app. All of it is defined as code in one bundle.

## Proof points mapped to evidence

| Claim | Evidence (text, in repo) |
|---|---|
| Data generated and pipeline ran with expectations | `evidence/data_*.txt` (row counts, expectation results) |
| UC tags, mask, row filter, grants applied | `evidence/data_governance*.txt`; `governance/01_apply_governance.py` |
| Model beats naive baseline (WAPE) | `evidence/ml_*metrics*.txt`; `gold_model_metrics` |
| Model registered and served | `evidence/ml_*endpoint*.txt` (sample response from `snb-cash-forecast`) |
| Baseline vs optimized KPIs | `evidence/ml_route_summary*.txt`; `gold_route_summary` |
| Lakebase synced tables and override write | `evidence/lakebase_*.txt` |
| Genie answers benchmark questions | `evidence/genie_*.txt` |
| App live and wired to real sources | `evidence/app_*.txt` (`/api/health`) |
| One job runs end to end | `evidence/e2e_*.txt`; `resources/e2e_job.yml` |
| Decisions and trade-offs | `docs/decisions.md` |

## Close (business-level)

> "On synthetic data this is about THB 1.5M a year in CIT cost, with fewer cash-outs and less idle cash, on a platform your architects can govern. I'd like to propose a 30-day pilot in Khon Kaen Central. Can we book two hours with Cash Ops and IT Security next week to scope the feeds?"

## Delivery reminders

- Tell, show, tell: say what you'll show, click, then say what it means in THB or SLA.
- Answer the CFO in one sentence of value, then stop. Give the architect the mechanism and the fallback.
- When unsure, say what you'd verify in the pilot. Don't invent numbers.
- Never name a real bank. Say "synthetic" once per results claim.
