# Right cash, right place — 30-minute spoken demo script

## 30-minute call plan

| Time | Focus | Outcome |
|---|---|---|
| 0:00–3:00 | Slides 1–4 | Confirm the problem, urgency, and agreed decision |
| 3:00–5:00 | Slides 5–7 | Explain root causes, architecture, and demo plan |
| 5:00–13:00 | Live app | Show current state, routes, forecast, override, and optional Genie |
| 13:00–15:00 | Slide 10 | Quantify and restate the outcome |
| 15:00–18:00 | Slide 11 | Separate what is ready from pilot gaps |
| 18:00–26:00 | Slide 12 and Q&A | Address blockers without overcommitting |
| 26:00–30:00 | Slide 13 | Ask for a measured pilot and assign next steps |

## Who's in the room

- **Nan:** Databricks solutions architect and presenter.
- **Alex Morgan:** executive sponsor for cash operations. Cares about cost, idle cash, cash-outs, customer trust, and a low-risk decision.
- **Shreya:** platform and data architect. Cares about security and PII, integration, production readiness, and operability.
- **Customer context:** a fictional regional bank in Northeast Thailand. Every number and record shown is synthetic.

## 1. Right cash, right place (00:00–00:45) · Slide 1

Say:

“Good morning, Alex. Good morning, Shreya. Thanks for making the time. Let me start with the plan. I’ll spend about thirteen minutes on the problem and the live app. Then we’ll look at readiness, risks, and next steps, with eight minutes for questions. Does that work for both of you? (pause)

From our last conversation, we agreed on one business outcome: reduce the cash sitting idle and lower the cost of moving it, without increasing cash-outs. Alex, is that still the right outcome to anchor on today? (pause)

Shreya, we also agreed that any solution has to pass two tests: it must protect sensitive data, and it has to be practical for your team to operate. Are those still the right technical priorities? (pause)

Great. I’ll use those two outcomes as the lens for the demo. One quick note: everything you’ll see uses synthetic data.”

*Keep the opening calm. Get one answer from each person; do not let discovery consume the demo.*

## 2. Where we are today (00:45–01:20) · Slide 2

Say:

“Let me start with the scope we agreed. Your cash operations cover 159 branches and 520 machines — 400 ATMs and 120 cash recyclers. They’re served by three cash centres and thirty armoured vans. Today, replenishment follows a fixed five-day cycle.

We’ve kept the MVP much tighter: one region, Khon Kaen, and one daily decision — where should cash go tomorrow? The outcome we agreed is less idle cash and fewer cash-outs, without trying to transform the whole network at once.”

## 3. What it costs today (01:20–02:05) · Slide 3

Say:

“Here’s what that looks like on the synthetic plan day. About 1.56 billion baht is sitting in machines and vaults. Only fourteen point seven percent of stops land inside opening hours. Sixty-four machines are at risk of cash-out. And the fixed cycle drives 135 stops and 1,711 kilometres, when the demand only needs 97 stops.

There’s a second lens: the cost of idle float. This is an assumption, not a bank figure. At an assumed two-percent cost of funds, releasing 43 million baht is worth roughly 0.9 million baht a year. The operating case doesn’t depend on that assumption.”

## 4. Why now (02:05–03:00) · Slide 4

Say:

“Alex, let me test the urgency with you. As PromptPay and QR reduce everyday cash use, a fixed cycle can overstock more each year. But New Year, Songkran, and payday peaks still create sharp local demand. At the same time, CIT and fuel costs are rising. When does the current CIT contract renew? (pause)

On this scenario, waiting adds about 125,000 baht a month in CIT cost alone. Which matters most right now: cost, cash-out risk, or the next planning and budget cycle? (pause) Got it. I’ll use that as the business lens for the rest of the discussion.”

## 5. Why it happens (03:00–03:50) · Slide 5

Say:

“Shreya, the root cause isn’t one bad route. The data is split across the ATM switch, vault and cash-centre systems, CIT trip logs, core banking, and holiday spreadsheets.

Then there’s the know-how. A driver may know a mall ATM opens late, but that stays in a radio call. Planning happens in Excel with day-old data and a calendar rule. There’s no forecast, no feedback loop, and no clean audit of overrides. Custodian PII and depot access don’t share one security model either.

So here’s the real issue: the data, the forecast, and people’s know-how never meet in one place.”

## 6. The solution in four steps (03:50–04:30) · Slide 6

Say:

“Shreya, let me show you what sits underneath. It’s four steps. First, unify the feeds with Lakeflow pipelines and govern them in Unity Catalog. Next, predict machine demand through Model Serving. Then decide tomorrow’s stops and routes with the optimizer. Finally, act through a Databricks App, with Lakebase for audited writes and Genie for governed questions.

The important part is the flow. Fragmented feeds become trusted data. Calendar rules become forecasts. Manual routes become explainable plans. And a radio call becomes an override we can audit.”

## 7. What I’ll show you (04:30–05:00) · Slide 7

Say:

“Here’s what I’m going to show. Overview gives us the current cash and risk. Route Tracking compares the fixed cycle with the optimized plan. Machines gives us a live ATM forecast. And Truck Detail shows how a dispatcher changes the plan without losing the audit trail.

If we have a minute, I’ll also ask one plain-language question. For each step, I’ll tell you what to watch, show it, then bring it back to the decision you need to make.”

## 8. Live app demo (05:00–13:00) · Slide 7 → App

### Overview

Say:

“Let me start with the current state. Watch these three measures: cash managed, idle cash, and machines at cash-out risk.”

**Click:** Open **Overview** and point to those KPI cards and the map.

Say:

“What you’re seeing is the same current state we just discussed, now down at node level on the map. So what does that mean for you, Alex? You can see where working cash is trapped and where customer trust is exposed. That’s our baseline before we optimize anything.”

### Route Tracking

Say:

“Next, I’ll compare the old cycle with a demand-based plan. Watch the stop count, kilometres, cost, and opening-hour SLA.”

**Click:** Open **Route Tracking**. Toggle **Baseline (fixed cycle)**, then **Optimized (CVRP-TW)**. Point only to the KPI cards row and map.

Say:

“The stop count falls from 135 to 97. Distance drops from 1,711 to 1,323 kilometres. And the opening-hour SLA moves from fifteen percent to a hundred.

Here’s the important trade-off. Vans rise from eleven to thirteen because two extra crews cover real demand inside the time windows. Even so, CIT cost falls from 75,400 to 69,550 baht a day because thirty-eight needless stops disappear. Alex, the plan uses more crews, but it moves less cash more effectively and costs less.”

*Do not point to the Route Summary donut or card percentage deltas.*

### Machines

Say:

“Now I’ll show where those demand signals come from. We’ll re-forecast one ATM and look at the busy-day range.”

**Click:** Open **Machines**. In **Machine Summary**, click row **A0004**. Scroll to the forecast panel. Click **Re-forecast**.

Say while waiting:

“This can take five to eight seconds if the endpoint has scaled to zero. While it warms, the production setting would match the morning planning window.”

Say:

“What you’re seeing is the P50 to P80 range, with **Model Serving · live** right here. On busy days, we plan near P80. That gives about 81 percent coverage, and a person still confirms the plan.

The overall forecast WAPE is 25 percent, compared with 39 percent for the naive rule. For ATMs, it’s 13 percent versus 25 percent. So we’re not just drawing a better route. We’re reducing the demand uncertainty that created those sixty-four cash-out risks.”

### Truck Detail and override

Say:

“A good route still needs local knowledge. Let me show you how a dispatcher changes the plan without losing accountability.”

**Click:** Open **Truck Detail**. Switch to **Optimized (CVRP-TW)**. Select a pending stop. Choose action **SKIP**. Enter reason **Branch closed for renovation**. Click **Submit override**.

Say:

“There’s the confirmation: **Saved override #N → Lakebase**. The dispatcher can act, and we keep the stop, user, reason, and time. Shreya, that’s the control that matters. Local knowledge stays useful, but it no longer disappears into a radio call. It becomes part of the audit trail and the next planning review.”

### Optional: Ask Cash Ops

Say:

“If we have one minute, I’ll show one self-service question: which nodes run out of cash in the next three days if we do nothing?”

**Click:** Open **Ask Cash Ops** and ask: **Which nodes run out of cash in the next 3 days if we do nothing?** Keep SQL collapsed.

Say:

“The answer is 79 critical nodes, with clean IDs. Here’s the important part: this isn’t a separate definition hidden in a chatbot. It comes from the same governed cash-operations data as the plan. The team can investigate quickly without creating a second version of risk.”

## 9. The outcome (13:00–15:00) · Slide 10

Say:

“Let me bring that together. On this synthetic day, CIT cost falls eight percent, from 75,400 to 69,550 baht a day — about 1.5 million baht a year. Distance falls 23 percent, from 1,711 to 1,323 kilometres. Cash-out risk goes from 64 to zero. The SLA moves from fourteen point seven percent to 100 percent. And the plan releases 43 million baht of idle cash.

Alex, that’s a lower-cost, lower-risk decision. Shreya, it’s one governed path from feed to forecast, plan, action, and audit. We’ve shown the operating outcome, not just the architecture.”

## 10. Production readiness (15:00–18:00) · Slide 11

Say:

“Now let’s separate what’s ready from what still needs work. The pipeline, job, and app are defined as code in one Databricks Asset Bundle. The design is serverless. The app runs as a service principal with scoped access. We have data-quality expectations, a model registered in Unity Catalog with a champion alias, and audited writes in Lakebase.

The gaps are just as important. In the pilot, we need to map row filters to your IdP groups and add maker-checker for overrides. We need dev and prod CI/CD targets, model-drift monitoring, and road-network travel times. Today, travel time is straight-line distance times 1.3. And we haven’t yet run the full job end to end on real feeds.

So the path is clear: Khon Kaen Central for thirty days, then all three cash centres, then harden and extend. The foundation is deployable. The pilot is where we prove the full operating path.”

## 11. Delivery risks and how we handle them (18:00–26:00) · Slide 12

Say:

“Let’s talk about the blockers we’re likely to hit.

If the ATM switch sits behind a firewall, that’s manageable. We can start safely with secure file drops into a Unity Catalog volume, then move to PrivateLink. I’d bring our networking and security specialist together with your network team to agree the path.

If the timeline slips, we don’t lower the success bar. We cut scope to one depot and file feeds first, keep the same criteria, and re-plan with Alex.

For PDPA and security sign-off, the data stays in your workspace and region. PII is masked, and system tables provide the audit evidence. I’d bring our security team into that review.

And on pricing, discounts, or contract terms, I won’t quote those here. Your account executive owns commercials, and I’ll set that up this week. Which of these feels like the first real blocker for your team? (pause) Thanks. That tells us who needs to be in the next working session.”

## 12. The ask and next steps (26:00–30:00) · Slide 13

Say:

“Let me close with the value and a clear ask. Alex, this is a low-risk way to reduce CIT movement and idle cash without trading away customer trust. Shreya, it’s a governed design with honest gaps and a measurable path to production.

I’m asking for a 30-day pilot in Khon Kaen Central. We’ll call it successful if CIT cost or kilometres fall by at least 20 percent, cash-outs are no higher than today, and dispatchers accept at least 80 percent of the recommendations.

The owners are clear. Alex, you sponsor a two-hour scoping session next week with the Cash Ops lead. Shreya, you bring IT Security and networking to agree the feeds and access. I’ll bring the account team for commercials and a Databricks networking and security specialist.

The numbers today are synthetic, so the pilot has to earn the decision on your data. What would you need to see to sponsor that next step? (pause)”

*Stop talking. Let Alex or Shreya answer.*

## 13. Backup: plan vs today (recovery only) · Slide 8

Say:

“The live app isn’t responding, so I’ll switch to the captured view and keep us moving. The fixed cycle shows 135 stops, 1,711 kilometres, sixty-four machines at risk, and fourteen point seven percent inside opening hours. The optimized plan shows 97 stops, 1,323 kilometres, zero at risk, and 100 percent inside opening hours. The result is still synthetic, so the pilot tests whether it holds on your feeds.”

## 14. Backup: forecast, override, ask (recovery only) · Slide 9

Say:

“This capture shows the three controls I wanted you to see. The forecast gives us a P50 to P80 range from live Model Serving. The override saves a skipped stop and its reason in Lakebase, so we know who changed what and why. Ask Cash Ops finds 79 critical nodes over the next three days. The app is the decision surface; the governed data and audit trail still sit underneath.”

## 15. Appendix: decisions and trade-offs (Q&A only) · Slide 14

Say:

“Here are the trade-offs we made. P80 lowers cash-out risk, but it can carry more cash. Thirteen vans meet every opening window, while thirty-eight unnecessary stops disappear and total cost still falls. A shared model is easier to govern, but we still need to test local payday behaviour. And the optimizer is explainable, but road-network travel times must replace today’s straight-line assumption.”

## 16. Appendix: under the hood (Q&A only) · Slide 15

Say:

“Shreya, here’s what sits underneath. Pipeline expectations reject bad records before planning. Custodian names and phone numbers are masked. Depot access is row-filtered, and lineage follows the data into the app. The forecast model is registered with a champion alias and served through a managed endpoint. The Asset Bundle keeps the pipeline, job, and app together. In the pilot, we map those controls to your identity groups and release process.”

## Blocker playbook

**Firewall or on-prem ATM switch**

“That’s a fair concern. We don’t need to make private connectivity the first critical path. We can start safely with secure file drops into a Unity Catalog volume, then move to PrivateLink. I’d bring a Databricks networking and security specialist together with your network team to agree the target design.”

**Timeline is slipping**

“If the timeline slips, I’d protect the outcome rather than pretend nothing changed. We’d cut scope to one depot and file feeds first, keep the same success criteria, and agree the re-plan with Alex. I wouldn’t commit to a new date until both teams had checked the dependencies.”

**PDPA or security sign-off**

“I’d expect that review, and we should plan for it. The data stays in your workspace and region. Custodian PII is masked, access is scoped, and system tables provide the audit evidence. I’d bring our security team into the session so your security and privacy owners can test the controls directly.”

**Pricing, discount, or contract terms**

“I won’t quote that here; your account executive owns commercials — I’ll set that up this week.”

**Are these numbers real?**

“They’re not production results. The data and outcomes are synthetic, which is why I’m proposing a measured pilot against the current cycle. We should earn the business case on your feeds, your routes, and your operating constraints.”

**Why are there more vans?**

“That’s the right trade-off to question. The old cycle skipped real demand and still made needless visits. The new plan adds two crews, from eleven to thirteen, to meet every opening window. At the same time, thirty-eight unnecessary stops disappear, so distance, stop count, and total cost still fall.”

**What if the model is wrong on payday?**

“That will happen sometimes, especially around payday. We plan to P80 on busy days rather than using an average. A dispatcher can override with a recorded reason, and a person confirms every plan before execution. In the pilot, we’ll measure payday error and dispatcher acceptance directly.”

## Reading the room

- If Alex leans into cost, stay on stops, kilometres, CIT cost, idle cash, and the measured pilot. Do not lead with platform terms.
- If Alex challenges thirteen vans, acknowledge the trade-off immediately and explain the thirty-eight needless stops removed.
- If Shreya asks about controls, move to slide 11 or 15. Distinguish what exists from what the pilot must add.
- If either person questions the synthetic results, agree and use that as the reason to run the pilot.
- At minute 18, stop presenting and invite objections. At minute 26, move to the ask even if every appendix question is not covered.

## Recovery lines

**App fails**

“The live app isn’t responding, so I’ll switch to the captured screens on slides eight and nine and keep us moving. I’ll show the same decisions, and we’ll treat live reliability as a pilot test item.”

**Forecast endpoint is cold**

“The endpoint scales to zero, so the first call can take five to eight seconds. While it warms, here’s the important part: we plan with the P50 to P80 band, then a dispatcher confirms the result.”

**Genie is slow**

“I won’t use your time waiting on an optional step. The benchmark answer is 79 critical nodes in the next three days. The pilot question is whether governed self-service speeds up the investigation without creating a second definition of risk.”

## Cut list if running long

1. Skip Ask Cash Ops first; save one minute.
2. Do not open slides 14 or 15 unless Shreya asks.
3. Reduce the forecast explanation to P80 coverage and live Model Serving; keep the exact WAPE figures for Q&A.
4. On slide 11, name the five gaps without elaborating on each.
5. Never cut the synthetic-data disclosure, production gaps, blocker judgment, success criteria, owners, or final open question.
