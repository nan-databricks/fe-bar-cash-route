# FE Bar requirements traceability

Honest status as of local repo check. Integrator updates after e2e.

| Requirement | Where | Status |
|---|---|---|
| Industry-specific customer problem | SNB CIT / cash-outs / idle cash — README, deck | Done (story) |
| Lakeflow ingest | `pipelines/snb_cash_ops_pipeline.py`, `resources/pipeline.yml` | Code in repo; **pipeline not proven in workspace yet** |
| Unity Catalog governance | `governance/01_apply_governance.py` | Code in repo; **not applied yet** |
| Lakebase operational serving | `lakebase/` (planned Wave 2) | **Missing** |
| ML or GenAI | `ml/01`–`04` LightGBM + OR-Tools | Code in repo; **not trained/served yet** |
| Genie Agent | `genie/` (planned Wave 2) | **Missing** |
| Databricks App | `app/` copied; still contains KTB strings | **Partial** — not rebranded, not deployed as `snb-cash-route` |
| Stages integrated | `resources/e2e_job.yml` | Job defined; **not run** |
| Text execution evidence | `evidence/` | **Missing** |
| Public GitHub | `{{GITHUB_URL}}` | **Missing** |
| Presentation deck PDF/md | `deck/deck.md` | **md Done; PDF pending render** |
| Outcome-first KPIs | deck slide 2, README | Done (illustrative until evidence) |
| Decisions and trade-offs | `docs/decisions.md` | Done |
| Quantified buyer KPIs | deck / README / form answers | Done (synthetic labels) |
| No real customer data | generator + naming contract | Done for data gen; **app still has KTB names** |
| Talk track / role-play prep | `docs/demo_script.md`, `docs/roleplay_prep.md` | Done |
| Submission form drafts | `docs/submission_form_answers.md` | Done; attestation Nan |
| Not from go/solution-builder | original repo | Done |
| GitHub readable by validator | public push | **Pending** |
