# SNB Cash Logistics — Databricks App `snb-cash-route`

Cash-in-transit (CIT) route optimization UI for **Siam Northeast Bank (fictional)**, Khon Kaen.
FastAPI backend + React 18 / Vite / Leaflet (OpenStreetMap) / Recharts frontend, served as a single
process: FastAPI serves `frontend/dist` at `/`.

Deployed URL: https://snb-cash-route-7474652587886975.aws.databricksapps.com (profile `nan-demo`).

## Data sources (each falls back to mock fixtures in `server/mock.py`)

| Feature | Live source | Endpoint |
|---|---|---|
| Nodes, trends, orders, routes, summary, model metrics | UC gold tables in `stable_classic_nan_fe_vm_catalog.snb_cash_ops` via SQL warehouse `23189fee7d892fb8` (Statement Execution API) | `GET /api/nodes`, `/api/orders`, `/api/routes?plan_type=OPTIMIZED\|BASELINE`, `/api/summary`, `/api/model-metrics` |
| 7-day re-forecast | Model Serving `snb-cash-forecast` (features from `gold_demand_features`) → else `gold_demand_forecast` → else mock | `POST /api/forecast {node_id}` |
| Dispatch overrides | Lakebase `snb-cash-ops` → `public.dispatch_overrides` (psycopg, OAuth token) | `GET/POST /api/overrides` |
| Ask SNB Ops | Genie space "SNB Cash Ops Assistant" (Conversation API) | `POST /api/genie/ask {question, conversation_id?}` |
| Health | reports which sources are live + last errors | `GET /api/health` |

UI-shaped adapters for the existing pages: `/api/machines`, `/api/branches`, `/api/branch-inputs`,
`/api/route-executions?plan_type=`. `POST /api/cache/clear` drops the 2-minute read cache.

## Environment variables (`app.yaml`)

| Var | Meaning |
|---|---|
| `CATALOG`, `SCHEMA` | UC location of gold tables |
| `WAREHOUSE_ID` | `valueFrom: sql-warehouse` resource |
| `SERVING_ENDPOINT` | `valueFrom: serving-endpoint` resource (`snb-cash-forecast`) |
| `GENIE_SPACE_ID` | Genie space id (empty → mock answers) |
| `PGHOST`, `PGDATABASE`, `PGUSER`, `PGPORT`, `PGSSLMODE` | injected when the Lakebase postgres resource is attached (missing → mock overrides) |
| `LAKEBASE_ENDPOINT` | `projects/snb-cash-ops/branches/<b>/endpoints/<e>` for `w.postgres.generate_database_credential`; empty → workspace OAuth token |
| `PLAN_DATE` | plan service date (default `2026-10-01`) |
| `USE_MOCK` | `true` forces fixtures everywhere |

Local defaults live in `config.yaml`.

## Run locally (ports 8010 / 5180)

```bash
cd app
uv venv -p 3.12 .venv && uv pip install -p .venv -r requirements.txt
DATABRICKS_CONFIG_PROFILE=nan-demo .venv/bin/uvicorn app:app --port 8010   # or USE_MOCK=true
cd frontend && npm install --legacy-peer-deps && npm run dev               # http://localhost:5180 (proxies /api → 8010)
```

Production build: `cd frontend && npm run build`, then open http://localhost:8010/ (FastAPI serves `dist`).
`?view=routes|detail|machines|branches|genie|...` opens a page directly.

## Deploy (CLI, not the bundle)

```bash
cd app/frontend && npm run build && cd ..
databricks sync --full --exclude "docs/**" . /Workspace/Users/nan.chulpaibul@databricks.com/apps/snb-cash-route -p nan-demo
databricks apps deploy snb-cash-route --source-code-path /Workspace/Users/nan.chulpaibul@databricks.com/apps/snb-cash-route -p nan-demo
```

`frontend/dist` is intentionally not git-ignored so `databricks sync` uploads it (there is no root
`package.json`, so Apps does not try to run an npm build).

App service principal: `4a12356e-6529-4f7b-b072-a5cbf47e909d` (`app-6acplc snb-cash-route`) — has
USE CATALOG, USE SCHEMA and SELECT on `snb_cash_ops`. To enable Lakebase/Genie, grant it a Postgres
role / CAN_RUN on the space, attach the postgres resource, set `GENIE_SPACE_ID` / `LAKEBASE_ENDPOINT`, redeploy.

Screenshots: `docs/screenshots/{overview,routes,detail,machines,genie}.png`.
