# FE Bar requirements traceability

Every requirement in `FE_Bar_Requirements_1.md`, where it is satisfied, and an honest status. **Status as of the narrative commit (2026-10-29); the integrator updates this after the end-to-end run and before submission.**

Status key: **Done** = in the repo and verifiable now · **Pending integrator** = code or doc exists but needs a run, a fill-in, or a publish step · **At risk** = a known gap that would cost points if not fixed · **Nan** = only Nan can do it.

## Part 1: The build

| # | Requirement | Where it is satisfied | Status |
|---|---|---|---|
| B1 | Working prototype solving a **customer problem in a specific industry** (not internal, not generic) | Banking CIT replenishment and routing for fictional SNB: `README.md`, `deck/deck.md` slides 2–4, `docs/submission_form_answers.md` | Done |
| B2 | **End-to-end data journey from a raw dataset** (synthetic or public) | `data/01_generate_data.py` → CSVs in `/Volumes/.../snb_cash_ops/raw`; `evidence/data_generate_run.txt` | Done (data generated) |
| B3 | **Lakeflow**: ingest the raw data | `pipelines/snb_cash_ops_pipeline.py` (Auto Loader, bronze/silver/gold, expectations), `resources/pipeline.yml`; `evidence/data_pipeline_events.txt`, `evidence/data_table_counts.txt` (bronze/silver/gold row counts) | Done on the Wave-1 scratch pipeline; **Pending integrator**: re-run as the bundle pipeline inside `snb_cash_ops_e2e` |
| B4 | **Unity Catalog**: govern it | `governance/01_apply_governance.py` (tags, `snb_mask_custodian`, `snb_depot_filter`, grants), `governance/README.md`; evidence expected at `evidence/data_governance*.txt` | Pending integrator (evidence file not yet committed) |
| B5 | **Lakebase**: operational serving | Planned in `lakebase/01_setup_lakebase.py` (project `snb-cash-ops`, synced `lb_route_stops`, `lb_node_status`, writable `public.dispatch_overrides`); app adapter `app/server/lakebase.py` | **At risk**: `lakebase/` is empty at the time of writing |
| B6 | **ML or Gen AI**: make it intelligent | `ml/01_train_register.py` (LightGBM point + P80, MLflow, UC registry), `ml/02_deploy_endpoint.py` (`snb-cash-forecast`), `ml/03_score_orders.py`, `ml/04_optimize_routes.py` (OR-Tools CVRP-TW); evidence expected at `evidence/ml_*.txt` | Pending integrator (code present; training/serving evidence not yet committed) |
| B7 | **Genie Agent**: make it queryable in natural language | `genie/space.yaml`, `genie/skills/`; deploy notebook `genie/01_deploy_genie.py` referenced by the job; evidence expected at `evidence/genie_*.txt` | Pending integrator (deploy notebook and benchmark evidence not yet in the repo) |
| B8 | **Databricks App**: surface it to the business | `app/` (React + FastAPI, `app/server/{serving,lakebase,genie,sql_client}.py`), app name `snb-cash-route`; evidence expected at `evidence/app_*.txt` | **At risk**: app still contains real-bank strings (see R1); deploy evidence pending |
| B9 | Stages **integrated, not siloed** | Single contract `contract/tables.yaml`; one job `resources/e2e_job.yml` chaining generate → pipeline → governance → train → serve → score → optimize → Lakebase + Genie; app reads the same gold/Lakebase/serving/Genie resources | Pending integrator (job defined; one full successful run must be logged to `evidence/e2e_*.txt`) |
| B10 | Submission includes **code, notebooks, app, dashboards** | `data/`, `pipelines/`, `governance/`, `ml/`, `lakebase/`, `genie/`, `app/` | Pending integrator (Lakebase and Genie code to land) |
| B11 | **Evidence the build ran, readable as text** (cell outputs, run logs, query results, model output) | `evidence/` (4 data files so far); README "Evidence that it ran" table maps each stage to its file | Pending integrator: ML, governance, Lakebase, Genie, app and e2e evidence still missing |
| B12 | Screenshots and recordings **don't count** on their own; source alone won't pass | All evidence is `.txt`; no screenshot-only claims in docs | Done (policy), contingent on B11 |
| B13 | **GitHub repo link required**, readable by the validator (public, or connected EMU) | `{{GITHUB_URL}}` in README, deck, form answers | Pending integrator: no git remote configured yet |
| B14 | **Never include real customer data**; scrub anything identifying a customer | Synthetic generator (seed 42026); fictional SNB; disclaimers in README, every deck slide footer, form answers | **At risk**: `app/frontend/src/App.tsx` (and earlier `app/app.py`, `app/frontend/src/data/branches.ts`) contained real-bank names and codes inherited from an earlier app template. The app owner must scrub them, and a repo-wide search for real bank names must return nothing before submission |

## Part 1: Presentation deck

| # | Requirement | Where it is satisfied | Status |
|---|---|---|---|
| D1 | Deck for the business audience, attached as PDF, .txt or .md | `deck/deck.md` (Marp source), `deck/deck.pdf`, `deck/build_pdf.sh` | Done (PDF built with placeholders); **Pending integrator**: fill KPIs and rebuild |
| D2 | **Lead with the business outcome** | Slide 1 headline is the outcome; slide 2 is the KPI table, before any architecture (slide 5) | Done |
| D3 | **Quantify impact in the buyer's KPIs** | Slides 1, 2 and 11: filled from `evidence/ml_route_summary.txt` and `evidence/ml_train_metrics.txt` (cost −8%, km −23%, cash-out 64→0, SLA 100%, WAPE 25% vs 39%) | Done |
| D4 | Frame value for **executive sponsor and domain owner** | Slide 4 "Who owns the decision" (CFO/COO vs Head of Cash Ops); slide 13 pilot ask | Done |
| D5 | Short **decisions and trade-offs** section | Deck slide 10; `docs/decisions.md`; README section | Done |
| D6 | Document **AI tools, prompts and patterns** used | README "AI tools and workflow"; form answer on AI tools | Done (Nan to personalise the wording) |
| D7 | Avoid "narrative skips business value and jumps to architecture" | Architecture first appears on slide 5, after outcome, problem and value | Done |

## Part 1: Submission form (Build tab)

| # | Field | Where | Status |
|---|---|---|---|
| F1 | Customer name | `docs/submission_form_answers.md` | Done |
| F2 | Industry / vertical | same | Done |
| F3 | Business challenge *(required)* | same | Done |
| F4 | How the solution addresses it *(required)* | same | Done |
| F5 | AI tools, workflow, decisions and trade-offs | same | Done (Nan to personalise) |
| F6 | Business outcomes and impact | same | Pending integrator (KPI placeholders) |
| F7 | GitHub repo link *(required)* | same, `{{GITHUB_URL}}` | Pending integrator |
| F8 | Presentation deck *(required)* | `deck/deck.pdf` | Pending integrator (rebuild after KPI fill) |
| F9 | Local repo folder *(required)* | `/Users/nan.chulpaibul/Documents/demo/Q42026/fe-bar-cash-route` | Done (path given); content complete once B5–B11 land |
| F10 | Conversation ID (optional) | session ID drafted | Nan to confirm |
| F11 | AI Customer Challenge checkbox | Leave unchecked (SNB is original); still includes a Lakeflow pipeline, a served model and a Genie agent | Done |
| F12 | **Attestation checkbox + typed full name** *(required)* | — | **Nan** (intentionally not filled) |

## Part 2: AI demo role-play

| # | Requirement | Where | Status |
|---|---|---|---|
| R-a | Present to a business and a technical persona in one session | `docs/roleplay_prep.md` personas | Done (prep) |
| R-b | Demo setup: frame customer, problem, what you'll show | `docs/demo_script.md` 0:00–0:45; `docs/roleplay_prep.md` opener | Done |
| R-c | Tell-show-tell | `docs/demo_script.md` (every step in tell/show/tell form) | Done |
| R-d | Value communication at executive level | KPI-led script; close in THB | Done (after KPI fill) |
| R-e | Reading the room | Persona table with pitch altitude; separate business vs technical answers | Done |
| R-f | Professionalism and objection handling | `docs/roleplay_prep.md`: business objections (cost, risk, time to value, adoption) and technical (security, real time, solver accuracy, data quality, Lakebase, Genie, Snowflake/Fabric, serverless cost, lock-in) | Done |
| R-g | Rehearse out loud; submit role-play after the build passes | — | **Nan** |

## Cheating policy and attestation

| # | Requirement | Status |
|---|---|---|
| C1 | Own work; not generated from go/solution-builder | Built from scratch against this repo's contract. **Nan** attests |
| C2 | No reuse of another FE's submission | **Nan** attests |
| C3 | AI tools used openly | Documented in README and form answers |

## Open risks (fix before submitting)

1. **Real-bank strings in `app/`** (B14, B8). This is a hard rule and must be scrubbed by the app owner.
2. **Lakebase stage has no code or evidence yet** (B5). A missing stage is a common reason for not passing.
3. **Execution evidence is incomplete** (B11): only data/pipeline files exist. ML metrics, endpoint response, route summary, governance output, Lakebase counts, Genie answers, app health and the e2e job run are all needed as text.
4. **No GitHub remote** (B13). The repo must be pushed and be public (or connected) before the form accepts it.
5. **KPI placeholders** (D3, F6) must be filled from evidence. Do not paste the format examples from `deck/PLACEHOLDERS.md` as results.
