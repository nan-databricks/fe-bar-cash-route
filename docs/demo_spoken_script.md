# Spoken demo script: SNB Cash Logistics (30-minute call, about 10 minutes of demo)

> **How to use this**
> 1. "Say:" is the words to speak. Read it out loud twice before the session, then talk, don't recite.
> 2. **Click:** is the one action to take. Say the line before it, then click, then pause.
> 3. Every section is tell, show, tell, and the closing tell names Alex or Shreya and ties to what they told you.
> 4. Slide numbers match `deck/slides.html`. In the app, keep Slide 5 (screenshot) ready as a backup.
> 5. Business words for Alex. Technical terms only in section 6, for Shreya.

**Who's in the room:** **Alex Morgan** (business persona): executive sponsor over Cash Operations at Siam Northeast Bank. Cares about CIT cost, idle cash, cash-out incidents, customer trust, and a low-risk decision. **Shreya** (technical persona): technical lead, platform and data architect. Cares about governance, security and PII, integration with existing systems, reliability, operability, scale, and lock-in.

## 30-minute call plan

| Time | What happens | Where |
|---|---|---|
| 0–2 | Setup: greet, agenda and time check, one discovery check each, restate the problem | Section 1 · Slides 1–4 |
| 2–12 | Demo: business view for Alex, then the handoff to Shreya | Sections 2–6 · App and workspace |
| 12–25 | Q&A: let them drive | `docs/roleplay_personas.md`, plus "If they ask…" below |
| 25–30 | Close: value for each of them, pilot ask, next step with owners | Section 7 · Slides 10 and 11 |

---

## 1. Set the stage (0:00–2:00) · Slides 1–4

*Slide 1 on screen. Look at the people, not the slide.*

Say: Good afternoon, Alex. Good afternoon, Shreya. Thanks for making the time.

Here's the plan. I've got about ten minutes of demo: first what it means for the business, then how it works underneath. Then I'd love to leave plenty of time for your questions, and we'll finish with next steps. Does that work for you both?

Before I show anything, two quick checks. Alex, is cash-out on payday still the biggest pain? And Shreya, anything you need to see on security that I should make sure I cover?

*Listen. Adapt:* Great, I'll spend a bit more time on that. *Then actually do it: more time in section 2 or 3 for Alex's pain, more in section 6 for Shreya's.*

*Slide 2.*

Say: So let me play back what I've heard. Siam Northeast Bank runs 159 branches and 520 cash machines across Khon Kaen. That's 400 ATMs and 120 cash recyclers, fed from 3 cash centres by 30 armoured vans. And every one of them gets cash every five days, whatever the demand.

*Slide 3.*

Say: Alex, Shreya, you each care about different parts of this, so I'll show both. Alex, for you that calendar means three things. Vans stop at machines that are still full. Payday ATMs run dry before the next visit, and that's customer trust on the line. And cash sits idle in cassettes and vaults, just in case. Shreya, for you, it means planning lives in yesterday's spreadsheets, outside anything you can govern.

*Slide 4.*

Say: Here's where we'll end up. Same machines, same day, a plan driven by demand instead of the calendar. Cash-in-transit cost drops from seventy-five thousand four hundred baht a day to sixty-nine thousand five hundred fifty. That's eight percent, or about one and a half million baht a year. Route kilometres fall twenty-three percent. And machines at risk of running empty go from sixty-four to zero.

One honest point up front: the new plan sends thirteen vans, not eleven. I'll explain why, because it's actually the good news. Quick note too: the bank and the data are synthetic, so treat the numbers as indicative.

*Bridge to the app:* Let me leave the slides and show you the real thing.

---

## 2. Tomorrow's plan vs today's cycle (2:00–3:45) · App (backup: Slide 5)

Say: Alex, this one's for you. Let's look at what tomorrow costs and what it risks.

**Click:** Route Tracking, then the **Baseline (fixed cycle)** toggle.

Say: This is how the vans run today. Eleven routes, about seventeen hundred kilometres. And notice this: fewer than fifteen percent of stops land inside branch opening hours. Sixty-four machines are still at risk of running dry.

**Click:** **Optimized (CVRP-TW)**.

Say: And this is the plan the platform built overnight from the forecast. Thirteen routes, about thirteen hundred kilometres. Every stop inside its time window. Zero machines at risk.

Look at the map. Instead of every van looping the whole province, each route sits tight around one cluster of machines. Each stop is there for a reason: how much cash, by when, and inside what window.

*Point only at the KPI cards row (cost/day, distance, vans, idle cash, cash-out risk, SLA, crew hours) and the map. Don't point at the Route Summary donut or the route status labels; they're simulated live tracking. Ignore the card percentage deltas: the SLA card says "▲ 580.3%", so say "fifteen percent to a hundred" instead.*

Say: So why more vans, but lower cost? The old cycle looked cheap because it was skipping real demand. It also made thirty-eight stops nobody needed. Those disappear, from 135 stops down to 97. That pays for the two extra crews and then some. And on-time goes from fifteen percent to a hundred.

Alex, you said cost and cash-outs matter most. That's about one and a half million baht a year in CIT cost, forty-three million baht of idle cash freed up, and no machines left to run dry, with no new vans to buy.

---

## 3. Re-forecast a machine (3:45–4:45) · App (backup: Slide 5)

Say: Alex, you mentioned payday. That's exactly where the fixed cycle breaks. So let me show you how the plan knows a machine's about to run out.

**Click:** Machines, then a row in the **Machine Summary** table, e.g. **SNB-A0004** (Very High risk ATM). Scroll to the forecast panel at the bottom of the page and click **Re-forecast**.

*Warm the endpoint before the session. Warm, the chart takes 5–8 seconds: fill it with "This is a busy ATM, and payday's coming." If it's cold (30–60 s): "The model scales to zero when nobody's using it, so the first call wakes it up. In production it stays warm before the morning run."*

Say: That's the forecasting model, called live. See the "Model Serving, live" tag. The line is expected cash demand for the next seven days. The shaded P50 to P80 band runs up to a busy day. We fill to the busy day on purpose. Why? Because an empty ATM costs you far more than one extra cassette.

And that forecast is what the route optimizer turns into orders. On this plan day that's 97 orders: 75 critical deliveries, 4 normal deliveries, and 18 pickups of surplus cash.

Alex, here's why that protects customer trust. The model's error is twenty-five percent, against thirty-nine percent for the "same day last week" rule. Your team knows which machines need them before payday, instead of guessing.

---

## 4. Dispatchers stay in control (4:45–5:30) · App (backup: Slide 5)

Say: No plan survives the morning untouched. Your dispatchers know things the data doesn't. So let me show you how they push back.

**Click:** Truck Detail. It opens on a Baseline route with every stop Completed, so switch to **Optimized (CVRP-TW)** first. Pick a pending stop (for example, the last stop on the route). In the overrides panel choose **SKIP**, type "Branch closed for renovation", then **Submit override**.

*Point at the "Saved override #N → Lakebase" confirmation, not the BY field (it shows local-user when run locally).*

Say: Done. That decision's saved, with the reason and who made it.

Alex, that's what makes this a low-risk decision. Your people still make the call, and every change has an audit trail instead of a phone call or a chat message. Nothing moves cash without a human saying yes.

---

## 5. Ask in plain language (5:30–6:45) · App (backup: Slide 6)

Say: Your team shouldn't need to raise a ticket just to ask a question. So let me ask the one that keeps Cash Ops up at night.

**Click:** Ask SNB Ops, then type: *Which nodes run out of cash in the next 3 days if we do nothing?*

*It usually answers in about 12 seconds. If it goes past about 20: "While that's thinking, here's the answer from our test run," then read it from Slide 6 or `evidence/genie_benchmarks.txt`. Read the headline answer and open the SQL. Don't walk through the table's days-to-cashout column, and ignore any stray \*\* symbols in the text.*

Say: There's the answer, in plain words. Seventy-nine machines and branches will run out within three days, and every one is flagged critical for a delivery. And here's the query it ran, so it's not a black box.

*Optional, if time allows:* **Click:** type *Compare optimized versus baseline CIT cost and km for 2026-10-01.*

Say: Same numbers you saw on the map. Seventy-five thousand four hundred down to sixty-nine thousand five hundred fifty. That's because it's the same data, not a separate report.

Alex, that's the early warning you'd want before a payday weekend, straight from the people who run the vans. Alex, does that answer the cost and cash-out question, or is there anything you'd want to see again?

*Wait for the answer. Then the handoff:*

Say: That's the business view. Shreya, how does it actually work?

---

## 6. Under the hood, for Shreya (6:45–9:30) · Workspace tabs (backup: Slides 7–9)

Say: Shreya, I know you'll want to see what's under the hood. You'd be the one running this, so let me show why it's one governed platform, not five tools taped together. Three stops: the pipeline, the governance, and the model.

**Click:** Lakeflow pipeline `snb_cash_ops_pipeline`.

Say: Eight raw feeds land in a governed volume and load incrementally. These quality rules drop bad records, like negative cash or missing IDs, before anything downstream sees them. And every update logs how many rows it dropped, so if one of your feeds is bad, you'll know on day one. That's your reliability story. And on integration: today these are files. In the pilot we'd point the same pipeline at your ATM switch, vault and van feeds, and nothing downstream has to change.

**Click:** Catalog Explorer, `silver_vehicles`, then `silver_cit_trips`.

Say: You asked about security. Custodian names and phone numbers are tagged as personal data and masked. And here, a row filter means each cash centre sees only its own trips. The assistant Alex just saw respects the same rules.

**Click:** Lineage on `gold_route_stops`.

Say: And this is the full path, from raw file to the table the app reads. When something looks wrong, you can trace it.

**Click:** MLflow experiment, then model `cash_demand_forecast@champion`, then endpoint `snb-cash-forecast`.

Say: The model's tracked, registered in Unity Catalog as champion, and served here. The overnight plan and that Re-forecast button use the same model.

Shreya, that's governance, security and operability in one place. One security model across SQL, machine learning, the assistant and the app. All serverless, so it scales without you managing clusters, and all defined as code in one bundle on open formats, so there's no lock-in trap and no second copy of the data to secure. Shreya, anything there you'd want to dig into?

*Wait. If it's deep detail, park it:* Great question. Let me note that and come back to it in Q&A.

*Bridge to Q&A:* That's the demo. I'd love to hear what's on your minds. Alex, Shreya, what questions do you have?

---

## 7. Close and next step (25:00–30:00) · Slides 10 and 11

*Slide 10.*

Say: Let me bring it back to what you both told me matters.

Alex, for you: about one and a half million baht a year in CIT cost, forty-three million baht of idle cash freed, and no machines left to run dry on payday.

Shreya, for you: one governed, secure platform your team can run, built from open formats and defined as code.

*Slide 11.*

Say: Now, this is synthetic data, so I don't want you to take it on trust. Here's what I'd propose. A thirty-day pilot in Khon Kaen Central, measured against today's cycle on the same machines. We'd call it a win if three things are true. CIT cost or kilometres fall by at least twenty percent. Cash-outs are no higher than today. And your dispatchers accept at least eighty percent of the recommended stops. It runs alongside today's process, humans confirm every plan, and the fixed cycle stays as the fallback. So the risk stays small.

So, a concrete next step. Alex, could you sponsor a two-hour scoping session next week with your Cash Ops lead? And Shreya, could you bring someone from IT Security, so we can agree the data feeds and the access model?

What would you need to see to say yes to the pilot?

*Stop. Let them answer. Fuller objection handling is in `roleplay_prep.md`.*

---

## Reading the room

- **Alex pushes on cost or ROI mid-demo:** answer in one line, then keep moving. "About one and a half million baht a year in CIT cost on this data. I'll walk through the full business case at the end." Then do it on Slide 10.
- **Shreya interrupts with deep tech:** answer in one or two sentences, then park it. "Short answer: yes, it's governed in Unity Catalog. Let me show you in a couple of minutes, and we can go deeper in Q&A." Watch the clock; the demo ends by minute 12.
- **Either of them goes quiet or looks disengaged:** ask them a question. Alex: "How does this compare with how payday runs today?" Shreya: "Is this close to how your team would want to operate it?"
- **Running behind:** use the cut list below. Protect Q&A time and the close.

---

## Recovery lines

- **Genie slow:** "While that's thinking, here's the answer from our test run." Read from Slide 6.
- **Endpoint cold start (30–60 s; warm it before the session):** "It scales to zero when idle, so the first call wakes it up. In production we keep it warm before the morning plan." Keep narrating the payday problem.
- **App won't load:** "Let me show you the same screen from this morning's run." Go to Slide 5 for sections 2–4, Slide 6 for section 5. Keep the same words.
- **"Why do most routes say Delayed?"** "That status panel is simulated live tracking for the demo. The plan itself meets every time window. That's the SLA card."
- **"Why are some days-to-cashout negative?"** (only if asked) "Negative means that machine is already below its safety level today. It's overdue, which is exactly why it's critical."

---

## If they ask…

- **Why does the van count go up? (Alex)** The old cycle looked cheap because it skipped demand. Sixty-four machines were at risk. Two extra crews buy a hundred percent on-time and zero cash-outs, and total cost still falls because thirty-eight needless stops go away.
- **Why not save even more vans? (Alex)** Because the time windows bind. Branches open for set hours, and critical machines have to be reached in those hours. Fewer vans means missed windows or cash-outs. The pilot will tell us if real travel times allow more.
- **Is this data real? (either)** No. The bank and every number are synthetic. That's exactly why the ask is a pilot on your own feeds, with success criteria you agree up front.
- **Security and PDPA? (Shreya)** Personal data is masked by column, trips are filtered by cash centre, and every access is logged. A formal PDPA review is part of hardening before any scale-up.
- **What does the platform cost? (Alex)** Honestly, I'd rather not guess. It's one nightly run, a model that scales to zero, and a small database, so it should be small next to a van-day. We'll scope pricing properly in the pilot and show you actual usage from week one.

---

## Cut list if running long

1. Skip the optional second Genie question.
2. Drop the MLflow click; keep the one sentence about the champion model.
3. Drop the lineage click; keep the mask and row filter.
4. Describe the override instead of clicking it.

Never cut: the discovery checks, the Baseline vs Optimized toggle, the van-count explanation, the handoff to Shreya, or the pilot ask with named owners.
