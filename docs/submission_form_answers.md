# Draft FE Bar submission answers

Nan pastes these into Skills Navigator. **Attestation and typed name: Nan to complete. Do not submit for him.**

## Customer name
Siam Northeast Bank (fictional regional bank)

## Industry / vertical
Banking / cash logistics (cash-in-transit)

## What is the business challenge you are solving? *(required)*
Siam Northeast Bank runs cash-in-transit on a fixed 5-day replenishment cycle across 159 branches and 520 ATM/RCM machines in Khon Kaen. Calendar visits waste van kilometres on nodes that are still full, leave too much idle cash in cassettes, and still miss payday and holiday spikes — so machines cash out. Dispatch cannot jointly answer “who needs cash tomorrow” and “which vans can cover them before 18:00.”

## How does your Databricks solution address this challenge? *(required)*
One integrated journey on Databricks: synthetic estate → Lakeflow bronze/silver/gold with data-quality expectations → Unity Catalog tags, custodian mask, depot row filter → LightGBM cash-demand forecast registered in UC and served on `snb-cash-forecast` → replenishment orders → OR-Tools CVRP-TW job writing comparable BASELINE vs OPTIMIZED routes → Lakebase synced stops plus writable dispatch overrides → Genie Agent space “SNB Cash Ops Assistant” → Databricks App control room for Cash Ops. The app is the business surface; every prior stage is an input, not a sidecar demo.

## What AI tools did you use, and what was your workflow? What decisions and trade-offs did you make?
Cursor Grok with a frozen table contract and parallel specialist agents (data/Lakeflow/UC, ML, app, narrative, then Lakebase and Genie). Databricks CLI on workspace profile `nan-demo`. Decisions: declarative pipeline vs notebooks; global LightGBM + P80 vs per-node models; OR-Tools time-capped CVRP-TW vs a commercial solver; Lakebase writeback vs warehouse-only app; Genie agent mode vs a custom agent. See `docs/decisions.md`.

## What are the business outcomes and impact?
On synthetic service date 2026-10-01 (placeholders until e2e evidence is filled): CIT cost/day THB 186k → 128k (**−31%**, ~**THB 14.5M/year**), **−27% km**, 26 → 18 vans, idle cash **−THB 42M**, cash-out risk nodes 19 → 2, SLA **98%**, forecast WAPE **18% vs 31%** naive. All figures are demo results on synthetic data, not a live bank.

## GitHub repo link *(required)*
`{{GITHUB_URL}}` — integrator publishes under Nan’s personal GitHub after scrub.

## Presentation deck *(required)*
`deck/deck.pdf` (source `deck/deck.md`). Talk track: `docs/demo_script.md`.

## Local repo folder *(required)*
`/Users/nan.chulpaibul/Documents/demo/Q42026/fe-bar-cash-route`

## Conversation ID *(optional)*
Cursor transcript for this build: parent session `e1a675d3-db0b-4072-9134-25bc32a69993`

## AI Customer Challenge checkbox
No. This is not NorthPeak / Meridian / Cedar / etc. It is a net-new fictional SNB cash-ops build (Lakeflow + trained/served model + Genie agent included).

## Attestation checkbox + typed full name
**Nan to complete.**

---

Currently still needed per form: Business challenge, Solution approach, Repository link, Presentation deck, Local repository folder, Attestation, Signed name.
