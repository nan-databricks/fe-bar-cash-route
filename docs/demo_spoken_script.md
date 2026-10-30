# Spoken demo script: SNB Cash Logistics (about 9 minutes)

Word-for-word script built on tell, show, tell. **Bold** = what to click. *Italic* = stage direction. Pause where you see "(pause)".

Audience: the CFO or COO (cost, float, risk) and the Head of Cash Operations (tomorrow's plan, control). If an architect is in the room, the "Under the hood" section is for them.

---

## 1. Setting the stage (0:00 to 1:00) · deck slides 1 to 3

*Slide 1 on screen.*

"Good afternoon, and thank you for the time. Before I show anything, let me check I've understood your world.

Siam Northeast Bank runs 159 branches and 520 cash machines across Khon Kaen, supplied from 3 cash centres with 30 armoured vans. Today every one of those points gets cash on a fixed 5-day cycle, whatever the demand.

From our conversations, that creates three problems for you. Vans visit machines that are still full. Payday ATMs run empty before the next visit. And cash sits idle in cassettes and vaults just in case. (pause)

Is that still the picture? *(Wait for a nod, or adjust.)*

*Slide 2.*

Here's where we'll end up. On the same day, with the same estate, a demand-driven plan cuts CIT cost by 8%, about THB 1.5 million a year. It cuts route kilometres by 23% and takes cash-out risk from 64 machines to zero. One honest point up front: it sends 13 vans instead of 11, because the fixed cycle was under-covering demand.

In the next eight minutes I'll show you three things. First, tomorrow's plan against today's cycle. Second, how a dispatcher works with it. Third, why your technology team can trust it. Everything you'll see runs on synthetic data, so treat the numbers as indicative."

---

## 2. The plan versus the old cycle (1:00 to 2:45)

**Tell:** "Let me start with what matters to you as CFO: what tomorrow costs."

**Show:** *Switch to the app.* Click **Route Tracking**, then the **Baseline (fixed cycle)** toggle.

"This is how the vans run today: 11 routes, 1,711 kilometres, and only 15% of stops arrive inside branch opening hours."

Click **Optimized (CVRP-TW)**.

"And this is the plan the platform built overnight: 13 routes, 1,323 kilometres, every stop inside its time window, and zero machines at risk of running dry."

*Point at the CIT cost card.*

"Cost per day goes from THB 75,400 to 69,550."

**Tell:** "So for you, that's about THB 1.5 million a year in CIT cost, plus THB 43 million of idle cash released, without buying a single new van. For Cash Operations, it means the plan is ready when you walk in at 7 a.m. Nobody builds it from yesterday's spreadsheet."

---

## 3. Re-forecasting a machine (2:45 to 3:45)

**Tell:** "Now for Cash Operations. Payday and holidays are where today's cycle breaks. Let me show you how the plan knows a machine is about to run dry."

**Show:** Click **Machines**, pick a machine marked Very High risk, then click **Re-forecast**.

"This calls our forecasting model live. The line is expected cash demand for the next 7 days, and the band is the busy-day level we replenish to. We deliberately plan for a busy day, because an empty ATM costs you more than one extra cassette."

**Tell:** "The model's error is 25%, against 39% for a same-day-last-week rule. That's the difference between guessing and knowing which machines need you this week."

---

## 4. The dispatcher stays in control (3:45 to 4:30)

**Tell:** "No plan survives the morning untouched. Your dispatchers know things the data doesn't, so let me show how they push back."

**Show:** Click **Truck Detail**. In the override panel choose **SKIP**, pick a low-priority stop, type "Branch closed for renovation", and click **Submit override**.

"That decision is now saved, with who made it and why."

**Tell:** "For you, that means an audit trail instead of a phone call or a chat message. Your team still makes the call. Nothing moves cash without a human confirming it."

---

## 5. Asking questions in plain language (4:30 to 5:45)

**Tell:** "Cash Ops shouldn't need a BI ticket to ask a question. Let me ask the system the question you asked me in our last meeting."

**Show:** Click **Ask SNB Ops** and type: *"Which nodes run out of cash in the next 3 days if we do nothing?"*

"It answers in plain language: 79 machines and branches will run out of cash within three days, all flagged critical for a delivery. And it shows the query it ran, so nothing is a black box."

*If time allows, ask:* "Compare optimized versus baseline CIT cost and kilometres for 1 October."

**Tell:** "It's answering from the same governed data as the plan, so a dispatcher in one cash centre only sees their own centre's data. The security rules apply here too."

*If Genie is slow:* "While that runs, this is the answer from our benchmark run." Then read it from `evidence/genie_benchmarks.txt`.

---

## 6. Under the hood, for your architect (5:45 to 7:30)

**Tell:** "For your technology team, I'll take ninety seconds to show why this is one governed platform rather than five tools taped together. I'll show three things: the data pipeline, the governance, and the model."

**Show:**
- **Lakeflow pipeline** `snb_cash_ops_pipeline`: "Eight raw feeds land in a governed volume and load incrementally. Here the quality rules drop bad records, such as negative cash or missing IDs, before anything downstream sees them."
- **Catalog Explorer**: open `silver_vehicles`. "Custodian names and phone numbers are tagged as personal data and masked." Then open `silver_cit_trips`. "A row filter means each cash centre sees only its own trips." Then open **Lineage** on `gold_route_stops`. "And here is the full path from raw file to the app."
- **MLflow and Serving**: "The model is tracked, registered in Unity Catalog as champion, and served on this endpoint. The overnight plan and the Re-forecast button use the same model."

**Tell:** "So you get one security model across SQL, machine learning, the assistant and the app, all serverless and defined as code in one bundle. There's no second copy of the data to secure."

---

## 7. Close and next step (7:30 to 9:00) · deck slides 12 and 14

**Tell, summarising:** "Let me bring it back to what you told me matters.

For you as CFO: about THB 1.5 million a year in CIT cost, THB 43 million of idle cash released, and zero machines at risk of running dry on the plan day.

For Cash Operations: a plan ready every morning, an audited way to override it, and answers without waiting on IT.

For your technology team: one governed platform your architects can run."

*Slide 14.*

"These are synthetic-data results, so I don't want you to take them on trust. My proposal is a 30-day pilot in Khon Kaen Central, measured against today's cycle on the same machines. We'd call it a success if three things are true. CIT cost or kilometres fall by at least 20%. Cash-outs are no higher than today. And your dispatchers accept at least 80% of the recommended stops.

As a next step, could we book two hours next week with your Cash Ops lead and IT Security to scope the data feeds? (pause)

What would you need to see to say yes to that pilot?"

*Stop talking. Let them answer. Objection handling is in `roleplay_prep.md`.*

---

## Delivery reminders

- Before you click, say what they're about to see. After you click, say what it means for them.
- Speak to a person, not the screen: "for you as CFO…", "for your dispatchers…".
- Slow down on the numbers: "seventy-five thousand four hundred… down to sixty-nine thousand five hundred fifty."
- Pause after each value statement. Silence reads as confidence.
- **If you're over time**, cut in this order: the second Genie question, the MLflow screen, then lineage. Never cut the baseline versus optimized toggle or the close.
- **If they ask why the van count goes up:** "The fixed cycle was cheap because it skipped demand: 64 machines were at risk. Two extra crews buy 100% SLA and zero cash-outs, and total cost still falls because 38 unnecessary stops disappear."
