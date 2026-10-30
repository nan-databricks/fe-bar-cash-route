# Role-play personas: Alex (business) and Shreya (technical)

Siam Northeast Bank (SNB) is fictional and every number is synthetic. Plan day is 2026-10-01, fixed 5-day cycle vs optimized. Say "on synthetic data" once per results claim. Slide numbers refer to `deck/slides.html`; app pages are in `snb-cash-route`.

## 1. Who you're talking to

**Alex Morgan, Business Persona (executive sponsor, Cash Operations).** Alex owns CIT cost, idle cash, cash-outs and the bank's reputation at the ATM. Alex also carries the risk if a change goes wrong in front of customers. Pitch at the P&L-and-risk altitude: THB per day and per year, machines at risk, on-time percentage, weeks to value. Use the words "cash-out", "van-day", "dispatcher", "pilot", never "CVRP" or "quantile". Good sounds like one sentence of value, one honest caveat, one next step. You'll lose Alex with architecture talk, overclaimed savings, or anything that sounds like dispatchers lose control.

**Shreya, Technical Persona (platform and data architect).** Shreya will run this, secure it and answer for it at audit. She cares about PDPA, who sees custodian data, how the core banking, ATM switch and CIT vendor feeds plug in, freshness, failure modes, MLOps, run cost, scale and lock-in. Pitch at the controls-and-contracts altitude: name the mechanism, the fallback and what's not built yet. Good sounds like "here's the control, here's where it's enforced, here's what I'd harden in the pilot." You'll lose Shreya by jargon-dumping, hand-waving a gap, or claiming production maturity the demo doesn't have.

## 2. Likely questions and answers

### Alex Morgan (business)

**1. "What's the ROI? When does it pay back?"**
On synthetic data, CIT cost drops from 75,400 to 69,550 baht a day. That's 8%, about 1.5 million baht a year, before the 43 million baht of idle cash freed up. I won't give you a payback date until we've measured run cost on your data. That's what the pilot's first week does. *Show it: Slide 12.*

**2. "Why are you sending more vans? That's more crews."**
Fair question. The old cycle looked cheap because it was skipping real demand. 64 machines were at risk of running dry, and only about 15% of stops hit their time window. The new plan drops 38 stops nobody needed, 135 down to 97. That pays for two extra crews, and total cost still falls. *Show it: Route Tracking, Baseline vs Optimized toggle.*

**3. "Are these numbers real?"**
No, and I want to be upfront about that. The bank and the data are synthetic, built to mirror a fixed 5-day cycle. So treat 8% as indicative. That's exactly why I'm proposing a 30-day pilot on your own feeds, with success criteria we agree before we start. Your numbers decide it, not mine.

**4. "Will my dispatchers actually use it?"**
They keep the final say. Any stop can be skipped, added, resequenced or flagged as an emergency, with a reason, and it's logged. The pilot target is 80% acceptance, not 100% automation. We'd design the override reasons with your dispatch lead in week one. Drivers still get a run sheet. *Show it: Truck Detail, submit a SKIP override.*

**5. "What if the model's wrong on payday?"**
It will be wrong sometimes, so we plan for it. We fill to the busy-day forecast, not the average. On the test data that covered about 81% of actual days. Payday and holidays are built into the model. And if something's off at 07:00, the dispatcher adds an emergency stop or re-forecasts that machine. *Show it: Machines, Re-forecast on SNB-A0004.*

**6. "Am I risking cash-outs during the pilot?"**
No more than today. The pilot runs alongside your current process in one cash centre. Humans confirm every plan. The fixed cycle stays as the fallback. And "cash-outs no higher than today" is one of the three success criteria. If it fails that, we stop.

**7. "How quickly do I see value?"**
The platform side is already built and deploys as code. The real work is connecting your feeds: ATM switch, vault balances and CIT trips. That's roughly six weeks, then a 30-day pilot measured against today's cycle in Khon Kaen Central. So you'd have a decision on real numbers in about a quarter. *Show it: Slide 13.*

**8. "What do you need from my team?"**
Three things. Two hours next week with your Cash Ops lead and IT Security to scope the feeds. A dispatch lead to co-design override reasons. And someone in finance to agree what a cash-out and a van-day really cost you, so the business case uses your numbers, not mine.

**9. "What does the platform cost?"**
I'd rather not guess a number. The workload is small: one nightly run, a forecast model that scales to zero when idle, and a small database. We'll measure actual run cost from the system billing tables in the pilot's first week, so you'll see a real figure next to the saving.

**10. "Why not stay with our CIT vendor's tool or the spreadsheet?"**
The routing is the easy part. The value is knowing each machine's demand before payday, keeping custodian data governed, and putting the plan, the overrides and the questions in one place. A routing tool still needs all of that fed to it. And the spreadsheet is what got you the fixed cycle. *Show it: Ask SNB Ops.*

### Shreya (technical)

**1. "How do you handle PII and PDPA?"**
Custodian name and phone are tagged as personal data in Unity Catalog and column-masked. Only the PII readers group sees clear text; everyone else gets asterisks. Every access lands in the audit system tables. A formal PDPA review, plus retention rules on custodian data, is part of hardening before scale-up. I won't claim it's certified today. *Show it: Catalog Explorer, `silver_vehicles`.*

**2. "How does row-level security map to our IdP groups?"**
The depot row filter checks group membership. In the demo it's one group per cash centre, like `snb_ops_kkn_c`. In production those become SCIM-synced groups from your IdP, so access follows HR, not tickets. If a pipeline-managed table rejects a direct filter, we expose a governed view instead. Same rule, different attachment point.

**3. "How do real feeds plug in: ATM switch, vault, CIT GPS?"**
Today there are eight raw feeds landing in a governed volume, loaded incrementally by Auto Loader. Real switch journals and vault balances replace the synthetic files via Lakeflow Connect or file drops, under the same silver contract, so nothing downstream changes. CIT GPS isn't in the demo. It'd be a new bronze feed, mainly for actual travel times. *Show it: Slide 5.*

**4. "How fresh is the data? What's the latency?"**
It's built for the morning plan: nightly forecast and solve, because vans load once at the cash centre. The Lakebase tables are snapshot syncs, so they're as fresh as the last job run, not streaming. Point reads are milliseconds. Continuous sync from the change feed is the production upgrade, and the pipeline can run continuously if you need intraday.

**5. "How do you monitor drift and retrain?"**
Honestly, monitoring isn't built in the demo. What is built: a time-based holdout, a naive baseline the model must beat, WAPE by segment, and a champion alias in Unity Catalog. In production I'd add monitoring on the inference tables, drift alerts and a champion-challenger flow. Retraining is a job task, so promotion is just moving the alias.

**6. "What if the serving endpoint is cold or down?"**
The morning plan doesn't wait on it. Routes are solved overnight and already sitting in Lakebase, so dispatch works either way. The endpoint scales to zero, so the first call takes 30 to 60 seconds. In production you'd keep it warm before the morning run. If it's down, only the Re-forecast button is affected, and the fixed cycle remains the fallback.

**7. "Will the optimizer scale to more depots?"**
It solves each depot separately, with a 25-second limit, so more depots mean more independent solves, not one giant problem. Today that's 97 orders across three depots. It's OR-Tools with guided local search: feasible and explainable, not provably optimal. Distances are straight-line times 1.3, not a road network. Real travel times and a commercial solver fit behind the same route tables.

**8. "Why Lakebase instead of our existing Postgres?"**
It is Postgres, version 17, so your team's skills carry over. The difference is that gold tables sync in from Unity Catalog without a separate ETL job, under the same governance. The app needs fast point reads plus one transactional write table for overrides. If Lakebase weren't an option, the fallback is warehouse reads and a Delta overrides table, with higher latency.

**9. "What about CI/CD and environments?"**
The pipeline and the end-to-end job are defined in one Asset Bundle. Each stage has run, and the evidence is in the repo. The full chain hasn't been run as one job yet, so I won't claim that. The app deploys separately today. For production I'd add dev, staging and prod targets, each run by a service principal.

**10. "How locked in are we?"**
Not much. Tables are Delta, readable as Iceberg. The model is an MLflow artefact. Lakebase is Postgres. OR-Tools is open source, and the app is React and FastAPI. Everything is code in one repo. The app's service principal has scoped grants, not admin, and we'd tighten those to gold-only in the pilot. *Show it: Slide 11.*

## 3. Bridge phrases

**Business to technical**
- "Alex, the reason you can trust that number is how the data's governed. Shreya, can I take ninety seconds on that?"
- "That's the business side. Shreya, you'd be the one running it, so here's what's under it."

**Technical to business**
- "Shreya, that's the mechanism. Alex, what it means for you is fewer surprises at 07:00."
- "So in plain terms: one security model, which is one fewer audit finding."

**Bringing a deep question back to value**
- "Happy to go deeper on that offline. The short answer is yes, with this fallback. What matters for the pilot is..."
- "Let me park the solver detail. I'll send a one-pager. The point is the plan's ready before your vans load."
- "That's a great pilot test. Can I write it down as a success criterion?"

## 4. Discovery questions (ask when they give you room)

**Alex**
1. "When a payday ATM runs dry today, what does it cost you: the emergency run, the complaints, the regulator?"
2. "Who decides tomorrow's stops today, and how long does it take each evening?"
3. "What would you need to see in 30 days to fund a second cash centre?"

**Shreya**
1. "Where do switch journals, vault balances and CIT handheld data land today, and how fresh is each one?"
2. "How are cash-centre staff grouped in your IdP, and is SCIM already in place?"
3. "What are your PDPA and data-residency constraints for custodian and transaction data?"

## 5. 30-minute call plan

| Time | Segment | What happens |
|---|---|---|
| 0–2 | Setup and discovery | 30-second opener (Slides 1–3). One check-in: "Does that match your world?" Repeat back any pain they add, and use it later. |
| 2–12 | Demo | Slide 2 outcome, then Route Tracking toggle, Machines re-forecast, Truck Detail override, Ask SNB Ops, then 90 seconds backstage for Shreya (pipeline, mask and row filter, model). Close each section with value for a named person. |
| 12–25 | Q&A | Answer at the asker's altitude, then bridge. Use discovery questions in natural pauses. |
| 25–30 | Close | Slide 12 recap in THB, Slide 14 pilot ask, three success criteria, book the two-hour scoping session. Ask: "What would you need to see to say yes?" |

**Time-management tips**
- Watch the clock at 12:00. If the demo runs long, cut MLflow, then lineage, then describe the override instead of clicking.
- Never cut the Baseline vs Optimized toggle, the van-count explanation or the pilot ask.
- Keep answers to 30–70 words, then stop. Silence is fine.
- If a question needs more than a minute, offer a follow-up and park it.
- At 25:00, start the close even mid-Q&A: "I want to respect your time, so let me pull this together."
- Warm the endpoint and open every tab before the call.

## 6. Never say

- "This is proven" or "you'll save 1.5 million." Say "indicative, on synthetic data."
- Any real bank's name, or that a real customer got these results.
- "The optimizer finds the optimal route." Say "feasible and explainable, not provably optimal."
- "It's real time" or "streaming." The Lakebase tables are snapshot syncs, refreshed each job run.
- "Road distances" or "traffic-aware." It's straight-line times 1.3.
- "That's live route tracking." The route-status donut is simulated.
- "It runs end to end as one job." Each stage ran; the bundle defines the full job.
- "Fewer vans." It's 13 vs 11, with lower total cost.
- Any platform price or payback date. Run cost is measured from system billing tables in the pilot's first week.
- "PDPA compliant" or "certified." Say the controls are in place and a formal review is part of hardening.
- "Zero cash-outs, guaranteed." Zero risk nodes on one synthetic plan day.
- Explaining negative days-to-cashout unless asked. If asked: "already below safety level, so it's overdue."
