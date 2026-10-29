# Talk track — 8 minute FE Bar role-play

Rehearse this **out loud** with `deck/deck.md` (or `deck/deck.pdf`) open, then the app. Timebox is strict: business persona first, technical persona will interrupt.

**Personas in the room**
- Business: CFO / Head of Cash Ops (funds CIT, owns cash-out SLA)
- Technical: Data platform lead / architect (UC, serving, Lakebase)

**Tell-show-tell rule:** name the outcome → click once → say what it means in THB or SLA.

---

## 0:00–0:45 · Setup (no slides of architecture yet)

> “Siam Northeast Bank is a fictional regional bank in Khon Kaen: 159 branches, 520 machines, 3 cash centres, 30 vans. Today cash logistics runs a **fixed 5-day cycle**. That wastes kilometres, parks too much idle cash in cassettes, and still lets payday machines cash out. I’m going to show a demand-driven plan for 1 October that cuts CIT cost about **31%** and cash-out risk from **19 nodes to 2**, on synthetic data — then how that plan is governed and served.”

Open slide 2 (KPI table). Do **not** walk the architecture yet.

---

## 0:45–2:30 · App: outcome on the map

Open Databricks App `snb-cash-route` → Executive / Route tracking.

| Time | You say | You show |
|---|---|---|
| 0:45 | “Same fleet, same day, two plans.” | KPI cards: cost / vans / SLA |
| 1:10 | “This is the calendar cycle — 26 vans, 19 nodes still at cash-out risk.” | Toggle **BASELINE** |
| 1:40 | “Optimized: 18 vans, 2 residual risk nodes, 98% of critical stops inside the window.” | Toggle **OPTIMIZED**, pan map |
| 2:10 | “For the CFO: that’s roughly **THB 14.5M/year** at 250 CIT days, without buying vans.” | Point at cost delta |

If the map is on mocks: say so in one clause (“live gold tables are in the workspace; the control room is wired to the same contract”) and keep moving.

---

## 2:30–3:30 · Re-forecast (ML serving)

Open a CRITICAL ATM or branch.

> “I’m not asking a planner to guess payday. This node’s 7-day demand comes from the **champion LightGBM** on endpoint `snb-cash-forecast`. We train on WAPE against a lag-7 naive — **18% vs 31%** — and we replenish off **P80**, because an empty ATM is more expensive than one extra cassette.”

Click **Re-forecast**. Speak only after the chart appears.

> “That curve is what turns into a DELIVER order with a time window the solver must honour.”

---

## 3:30–4:15 · Override (Lakebase write)

On Route detail:

> “Dispatchers will disagree. That’s a feature. Skip this healthy stop, type a reason — the write goes to Lakebase `dispatch_overrides`, not a WhatsApp thread. Tomorrow’s job can see it. Audit can see it.”

Submit SKIP. Confirm it lists back from GET.

---

## 4:15–5:15 · Genie Agent

Open **Ask SNB Ops**.

Ask 1: *Which nodes run out in the next 3 days if we do nothing?*  
Ask 2: *What is CIT cost of optimized vs baseline for 2026-10-01?*

> “Genie is not a chatbot on PDFs. It is a space over gold tables with joins and agent mode, so Cash Ops can ask the same questions without waiting for a BI ticket. Answers are SQL you can show the architect.”

If Genie is not live, read the committed answers from `evidence/genie_benchmarks.txt` and say they are the space’s benchmark pack.

---

## 5:15–6:30 · Backstage for the architect (only if they haven’t already grabbed the keyboard)

Keep this to **three clicks**:

1. Lakeflow pipeline `snb_cash_ops_pipeline` — event log / expectations (not “we have a pipeline”).
2. UC `silver_vehicles` — custodian column **masked**; mention depot **row filter** on trips.
3. MLflow run + serving endpoint Ready + `gold_route_summary` query.

Script:

> “Raw CSVs land in a UC volume. Lakeflow types and tests them. Gold features train the model; gold orders feed OR-Tools; gold stops sync to Lakebase; the app and Genie both read the same tables. One catalog, one job in the bundle.”

Do not mention Snowflake, Fabric, or a real bank.

---

## 6:30–7:30 · Close and the ask

Back to slide “Ask”.

> “Pilot **one cash centre for 30 days**. Success is ≥20% CIT cost or km down, cash-outs not worse, dispatchers accepting ≥80% of recommended stops. Humans still confirm the plan — we are not moving cash autonomously. The architecture is already the production shape; the increment is their telemetry on this contract.”

Stop talking. Let them object. Use `docs/roleplay_prep.md`.

---

## If you run long, cut in this order

1. Drop MLflow UI (keep the WAPE sentence).
2. Drop Genie question 2.
3. Drop override if Lakebase is mock — say the table contract and move on.

Never cut the KPI table or the BASELINE vs OPTIMIZED toggle.
