# Demo script: SNB Cash Logistics (8–9 minutes, 10 max)

Rehearse out loud with `deck/deck.pdf` open in one tab and these open in others: the **App** `snb-cash-route`, the **Genie space** "SNB Cash Ops Assistant", the **Lakeflow pipeline** `snb_cash_ops_pipeline`, **Catalog Explorer** on `stable_classic_nan_fe_vm_catalog.snb_cash_ops`, the **MLflow experiment** `snb_cash_forecast` and **Serving** `snb-cash-forecast`.

Fill `{{...}}` with real run values first (`deck/PLACEHOLDERS.md`).

**Rule for every step: tell, show, tell.** Say the outcome you're about to show, click once, then say what it means in THB, SLA or risk.

**Room:** business persona (CFO or Head of Cash Ops) and technical persona (architect or data platform lead). Business first; the architect gets the backstage section.

---

## 0:00–0:45 · Setup (deck slides 1–2, no architecture yet)

> "Siam Northeast Bank is a fictional regional bank in Khon Kaen: 159 branches, 520 machines, 3 cash centres, 30 vans. Today every machine gets cash every 5 days, whatever the demand. That wastes kilometres, parks idle cash, and still lets payday ATMs run empty.
> I'll show you three things: the plan for 1 October compared with the old cycle, how a dispatcher works with it, and why your architects can trust it. On synthetic data, the plan cuts CIT cost by 8% and cash-out risk from 64 nodes to 0."

Show slide 2 (KPI table) for 10 seconds, then switch to the App.

---

## 0:45–2:30 · App: the outcome on the map

| Time | Say (tell) | Click (show) | Say (tell: what it means) |
|---|---|---|---|
| 0:45 | "Same fleet, same day, two plans." | App home: KPI cards | |
| 1:05 | "This is the fixed cycle." | Toggle **BASELINE** | "11 vans, 64 machines still at risk of running dry." |
| 1:35 | "Now the demand-driven plan." | Toggle **OPTIMIZED**; pan to Khon Kaen city | "13 vans, −23% km, 100% of stops inside opening hours." |
| 2:00 | "For the CFO:" | Point at the cost card | "THB 75,400 down to 69,550 a day, about THB 1.5M a year, without buying a new fleet — we actually dispatch two more vans so SLA is 100%, not 15%." |
| 2:15 | "For Cash Ops:" | Open the **Orders** list, sorted by priority | "Every stop has a reason: amount, days to cash-out, time window." |

If the app shows mock data, say so in one clause ("the live gold tables are in the workspace; this view uses the same contract") and keep moving.

---

## 2:30–3:30 · Re-forecast (ML on Model Serving)

Pick a CRITICAL ATM near a payday date.

> "Planners shouldn't have to guess payday. This machine's next 7 days come from our champion model, live on the serving endpoint."

Click **Re-forecast** and wait for the chart.

> "The solid line is expected demand; the band is P80. We replenish to P80 because an empty ATM costs more than one extra cassette. On the holdout, the model's error is 25% WAPE against 39% for a naive method. That forecast is what turned into the DELIVER order the solver had to fit into a time window."

---

## 3:30–4:15 · Dispatcher override (Lakebase write)

Open a route and choose a healthy, low-priority stop.

> "Dispatchers will disagree with the plan sometimes, and that's a feature."

Choose **SKIP**, type the reason "Branch closed for renovation", and submit. Show that it lists back.

> "That override is written to Lakebase, our operational Postgres, with who and why. Audit can see it, and tomorrow's plan can take it into account. It doesn't end up in a WhatsApp thread."

---

## 4:15–5:30 · Genie agent (natural language)

Use the Genie chat in the app, or the Genie space itself.

1. *"Which ATMs are at risk of cashing out in the next 3 days if we do nothing?"*
2. *"Compare optimized vs baseline CIT cost and km for 2026-10-01."*
3. (If time) *"Which van covers the critical stops from Khon Kaen Central, and in what order?"*

> "Cash Ops can ask this themselves, without a BI ticket. It's Genie in agent mode over the governed gold tables, so it respects the same masks and row filters. Show the SQL to the architect: no black box."

If Genie is slow, read the committed answer from `evidence/genie_*.txt` and say it comes from the space's benchmark run.

---

## 5:30–7:30 · Under the hood (for the architect, three stops)

**Lakeflow (≈ 40 s).** Open pipeline `snb_cash_ops_pipeline` and show the graph.
> "Raw CSVs land in a Unity Catalog volume. Auto Loader picks them up incrementally, silver enforces expectations (here's how many rows we dropped for null keys or negative cash), and gold builds the features and status the model and app use. Declarative, serverless, with an event log."

**Unity Catalog (≈ 50 s).** Catalog Explorer → `silver_vehicles` → columns.
> "Custodian name and phone are tagged PII and masked; I see `***` unless I'm in the PII readers group."

Open `silver_cit_trips`: row filter by depot.
> "A dispatcher in one cash centre sees only their trips."

Open the **Lineage** tab on `gold_route_stops`.
> "From raw file to the table the app syncs, in one graph. One governance model for SQL, ML, Genie and the app."

**MLflow + Serving (≈ 30 s).** Open the experiment's latest run: metrics `WAPE_model` and `WAPE_naive`. Then the model `cash_demand_forecast` with alias `champion`, then endpoint `snb-cash-forecast` showing Ready.
> "Tracked, registered in Unity Catalog, served. The overnight batch and the app's button use the same champion."

Wrap with one sentence:
> "It's all defined as code in one Asset Bundle: pipeline, job `snb_cash_ops_e2e` and app."

---

## 7:30–8:30 · Close (back to the deck: business case, then the ask)

> "So: on synthetic data, about THB 1.5M a year in CIT cost, cash-out risk from 64 nodes to 0, and THB 43M of idle cash released, on a platform your architects can govern.
> My proposal: a 30-day pilot in Khon Kaen Central. Success means ≥ 20% lower CIT cost or km, cash-outs no higher, and dispatchers accepting at least 80% of planned stops. Humans confirm every plan. Can we book two hours with Cash Ops and IT Security to scope the feeds?"

Stop talking and let them object. Answers are in `docs/roleplay_prep.md`.

---

## If you run long, cut in this order

1. Third Genie question
2. MLflow UI (keep the WAPE sentence)
3. Lineage graph (keep mask + row filter)
4. Override: describe it instead of clicking

Never cut the KPI slide, the BASELINE vs OPTIMIZED toggle, or the close.

## Pre-flight checklist (5 min before)

- [ ] Endpoint `snb-cash-forecast` is Ready (warm it with one query, since it scales to zero)
- [ ] SQL warehouse is running (Genie and Catalog Explorer)
- [ ] App `/api/health` reports `lakebase: true` and the endpoint name
- [ ] Genie space opens; one warm-up question asked
- [ ] All `{{...}}` placeholders replaced in the deck you're presenting
