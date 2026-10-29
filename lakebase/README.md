# Lakebase — `snb-cash-ops`

Lakebase Autoscaling project that serves the SNB Cash Logistics app at low latency.

| Item | Value |
|---|---|
| Project | `projects/snb-cash-ops` (Postgres 17) |
| Branch / endpoint | `production` / `primary` (read-write, autoscaling) |
| Endpoint path | `projects/snb-cash-ops/branches/production/endpoints/primary` |
| PGHOST | `ep-rapid-thunder-d1691ize.database.us-west-2.cloud.databricks.com` |
| Database | `databricks_postgres` |

## Objects

| Postgres object | Kind | Source | PK | Mode |
|---|---|---|---|---|
| `snb_cash_ops.lb_node_status` | UC synced table (read-only) | `gold_node_status` | `node_id` | SNAPSHOT |
| `snb_cash_ops.lb_route_stops` | UC synced table (read-only) | `gold_route_stops` (CDF on) | `service_date, plan_type, route_id, stop_seq` | SNAPSHOT |
| `public.dispatch_overrides` | Writable table (app writes) | — | `override_id` | — |

The synced tables are also visible in Unity Catalog as
`stable_classic_nan_fe_vm_catalog.snb_cash_ops.lb_node_status` / `lb_route_stops`.

```sql
CREATE TABLE IF NOT EXISTS public.dispatch_overrides (
  override_id  BIGSERIAL PRIMARY KEY,
  service_date DATE NOT NULL,
  route_id     TEXT,
  node_id      TEXT,
  action       TEXT NOT NULL CHECK (action IN ('SKIP','ADD','RESEQUENCE','EMERGENCY')),
  reason       TEXT,
  created_by   TEXT,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS dispatch_overrides_date_idx ON public.dispatch_overrides (service_date, route_id);
```

## Setup

`01_setup_lakebase.py` is an idempotent notebook for the `snb_cash_ops_e2e` job (run it after the ML task).
It creates the project if it is missing, ensures `dispatch_overrides`, enables CDF on `gold_route_stops`,
creates or refreshes both synced tables, and grants the app identity. Widgets:

| Widget | Default | Notes |
|---|---|---|
| `app_sp_client_id` | `4a12356e-6529-4f7b-b072-a5cbf47e909d` (app `snb-cash-route`) | If empty, looks up the app SP; if there is no app, grants `fallback_user`. Lakebase `role_id` is `sp-<client-id>` because IDs must start with a letter. |
| `fallback_user` | `nan.chulpaibul@databricks.com` | |

Grants applied to the app identity:

```sql
GRANT CONNECT ON DATABASE databricks_postgres TO "<grantee>";
GRANT USAGE ON SCHEMA public TO "<grantee>";
GRANT SELECT, INSERT, UPDATE, DELETE ON public.dispatch_overrides TO "<grantee>";
GRANT USAGE, SELECT ON SEQUENCE public.dispatch_overrides_override_id_seq TO "<grantee>";
GRANT USAGE ON SCHEMA snb_cash_ops TO "<grantee>";
GRANT SELECT ON ALL TABLES IN SCHEMA snb_cash_ops TO "<grantee>";
ALTER DEFAULT PRIVILEGES IN SCHEMA snb_cash_ops GRANT SELECT ON TABLES TO "<grantee>";
```

The service principal also needs a Lakebase role on the branch first (the notebook creates it):

```bash
databricks postgres create-role projects/snb-cash-ops/branches/production \
  --role-id <sp-client-id> \
  --json '{"spec": {"identity_type": "SERVICE_PRINCIPAL", "postgres_role": "<sp-client-id>", "auth_method": "LAKEBASE_OAUTH_V1"}}' \
  -p nan-demo
```

## Connecting from the app

Environment (`app.yaml`):

```yaml
env:
  - name: PGHOST
    value: ep-rapid-thunder-d1691ize.database.us-west-2.cloud.databricks.com
  - name: PGDATABASE
    value: databricks_postgres
  - name: LAKEBASE_ENDPOINT
    value: projects/snb-cash-ops/branches/production/endpoints/primary
```

Python (psycopg 3). The OAuth token expires after about 1 hour, so mint a fresh one per connection (or per pool refresh):

```python
import os
import psycopg
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()  # inside a Databricks App this authenticates as the app service principal
ENDPOINT = os.environ.get("LAKEBASE_ENDPOINT", "projects/snb-cash-ops/branches/production/endpoints/primary")


def generate_database_credential() -> str:
    # Equivalent to: databricks postgres generate-database-credential <ENDPOINT>
    return w.api_client.do("POST", "/api/2.0/postgres/credentials", body={"endpoint": ENDPOINT})["token"]


def pg_connect():
    return psycopg.connect(
        host=os.environ["PGHOST"],
        port=5432,
        dbname=os.environ.get("PGDATABASE", "databricks_postgres"),
        user=w.current_user.me().user_name,  # the SP's application id when running as the app
        password=generate_database_credential(),
        sslmode="require",
    )


with pg_connect() as conn:
    conn.execute(
        "INSERT INTO public.dispatch_overrides (service_date, route_id, node_id, action, reason, created_by) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        ("2026-10-01", "R-KKN-C-01", "ATM-0001", "SKIP", "site closed", "ops@snb"),
    )
    rows = conn.execute("SELECT * FROM snb_cash_ops.lb_node_status LIMIT 5").fetchall()
```

From a laptop:

```bash
export PGHOST=ep-rapid-thunder-d1691ize.database.us-west-2.cloud.databricks.com
export PGPASSWORD=$(databricks postgres generate-database-credential \
  projects/snb-cash-ops/branches/production/endpoints/primary -p nan-demo -o json | jq -r .token)
psql "host=$PGHOST port=5432 dbname=databricks_postgres user=nan.chulpaibul@databricks.com sslmode=require"
```
