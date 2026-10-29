# Talk track (short card)

Full timed script: [`demo_script.md`](demo_script.md). Objections: [`roleplay_prep.md`](roleplay_prep.md).

**Open:** "Fixed 5-day CIT cycles waste kilometres, park idle cash, and still let payday ATMs run empty."
**Outcome:** "Same day, synthetic data: cash-out risk 64 → 0, SLA 15% → 100%, km −23%, cost −8% (~THB 1.5M/year). Two extra vans on purpose — the calendar plan was under-covering."
**Show:** App BASELINE vs OPTIMIZED → Re-forecast → override written to Lakebase → Genie "cash-out in 3 days" question → pipeline, UC mask and row filter, MLflow.
**Architect one-liner:** "Volume → Lakeflow expectations → UC mask and row filter → champion model on serving → CVRP-TW → Lakebase + Genie + App. One catalog, one bundle, one job."
**Ask:** "Pilot one cash centre for 30 days: ≥ 20% lower cost or km, cash-outs no higher, 80% dispatcher acceptance. Humans confirm every plan."
