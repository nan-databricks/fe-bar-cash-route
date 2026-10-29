# Genie Agent: SNB Cash Ops Assistant

Natural-language Q&A over the SNB cash-ops gold tables in `stable_classic_nan_fe_vm_catalog.snb_cash_ops`.

- **space_id:** `01f1d39a6e5c1bee90888b41e5e55e66`
- **URL:** https://fevm-stable-classic-nan-fe-vm.cloud.databricks.com/genie/rooms/01f1d39a6e5c1bee90888b41e5e55e66
- **Warehouse:** `23189fee7d892fb8` (Serverless Starter), profile `nan-demo`
- **Benchmark answers:** [`../evidence/genie_benchmarks.txt`](../evidence/genie_benchmarks.txt)

The app reads it through `GENIE_SPACE_ID` (or `genie_space_id` in `app/config.yaml`).

## Tables in the space

Pipeline gold (always): `gold_cash_nodes`, `gold_node_daily`, `gold_demand_features`, `gold_node_status`, `gold_baseline_daily`.

ML gold (added when present): `gold_model_metrics` (present now), `gold_demand_forecast`, `gold_replenishment_orders`,
`gold_routes`, `gold_route_stops`, `gold_route_summary`.

At the last deploy, the forecast, orders and route tables did not exist yet. Until they do, the space answers cash-out
risk from `gold_node_status` (current cash / 28-day average outflow), and for optimized-vs-baseline questions it says
the route job has not landed rather than inventing numbers. **Re-run `01_deploy_genie.py` after `optimize_routes`** (the
e2e job does this: `genie_space` depends on `optimize_routes`) to attach the route tables, their joins and the route
example SQL.

## Files

| File | What |
|---|---|
| `space.yaml` | Instructions, tables, value dictionaries, joins, example SQL, SQL snippets, sample questions, benchmarks |
| `01_deploy_genie.py` | Databricks notebook (source format). Finds the space by title, then creates or PATCHes it. Only attaches tables that exist. Uploads the skills. Prints `SPACE_ID=` and `URL=` |
| `skills/*/SKILL.md` | Agent-mode skills: `cash-out-risk`, `cit-cost-compare`, `idle-cash-by-depot`, `vans-used`. Uploaded to `/Workspace/Users/nan.chulpaibul@databricks.com/.assistant/skills/` |
| `run_benchmarks.py` | Asks the live space 6 questions (Conversation API) and writes `evidence/genie_benchmarks.txt` |

## Run

```bash
# create / update the space (local, uses profile nan-demo; also runs as e2e task genie_space)
cd genie && python3 01_deploy_genie.py

# re-run benchmarks against the live space -> evidence/genie_benchmarks.txt
python3 genie/run_benchmarks.py --space-id 01f1d39a6e5c1bee90888b41e5e55e66
```

## Agent mode and skills

The text instructions route each question to one of the four skills, and each skill sets the answer format. Agent mode
(the toggle in the Genie UI) runs multi-step questions. Skills are loaded by Genie One / the assistant from
`.assistant/skills`; the Genie Agent itself follows the same routing through its instructions and example SQL.
