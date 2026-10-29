# Databricks notebook source
# MAGIC %md
# MAGIC # SNB Cash Ops — Lakebase setup (idempotent)
# MAGIC
# MAGIC Sets up the Lakebase Autoscaling project `snb-cash-ops` for the SNB Cash Logistics app:
# MAGIC
# MAGIC 1. Create the project (production branch + `primary` read-write endpoint) if it is missing.
# MAGIC 2. Create the writable table `public.dispatch_overrides` in `databricks_postgres`.
# MAGIC 3. Enable Change Data Feed on `gold_route_stops` (if the table exists).
# MAGIC 4. Create the UC synced tables `lb_node_status` and `lb_route_stops` (SNAPSHOT), or re-run their sync pipelines if they already exist.
# MAGIC 5. Grant the Databricks App service principal (or the fallback user) access.
# MAGIC
# MAGIC Safe to re-run: every step checks state first.

# COMMAND ----------

# MAGIC %pip install -q "psycopg[binary]>=3.1"
# MAGIC %restart_python

# COMMAND ----------

dbutils.widgets.text("catalog", "stable_classic_nan_fe_vm_catalog")
dbutils.widgets.text("schema", "snb_cash_ops")
dbutils.widgets.text("project_id", "snb-cash-ops")
dbutils.widgets.text("app_name", "snb-cash-route")
dbutils.widgets.text("app_sp_client_id", "4a12356e-6529-4f7b-b072-a5cbf47e909d")
dbutils.widgets.text("fallback_user", "nan.chulpaibul@databricks.com")

CATALOG = dbutils.widgets.get("catalog")
SCHEMA = dbutils.widgets.get("schema")
PROJECT_ID = dbutils.widgets.get("project_id")
APP_NAME = dbutils.widgets.get("app_name")
APP_SP_CLIENT_ID = dbutils.widgets.get("app_sp_client_id").strip()
FALLBACK_USER = dbutils.widgets.get("fallback_user").strip()

BRANCH = f"projects/{PROJECT_ID}/branches/production"
ENDPOINT = f"{BRANCH}/endpoints/primary"
PG_DATABASE = "databricks_postgres"

SYNCED_TABLES = [
    {"name": "lb_node_status", "source": "gold_node_status", "pk": ["node_id"]},
    {"name": "lb_route_stops", "source": "gold_route_stops", "pk": ["service_date", "plan_type", "route_id", "stop_seq"]},
]

# COMMAND ----------

import time

from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import NotFound

w = WorkspaceClient()
api = w.api_client


def get_or_none(path):
    try:
        return api.do("GET", path)
    except NotFound:
        return None


def wait_until(fn, desc, timeout_s=900, every_s=15):
    deadline = time.time() + timeout_s
    while True:
        result = fn()
        if result:
            return result
        if time.time() > deadline:
            raise TimeoutError(f"Timed out waiting for {desc}")
        print(f"waiting for {desc} ...")
        time.sleep(every_s)


def table_exists(full_name):
    return spark.catalog.tableExists(full_name)

# COMMAND ----------

# MAGIC %md ## 1. Project, branch, endpoint

# COMMAND ----------

if get_or_none(f"/api/2.0/postgres/projects/{PROJECT_ID}") is None:
    print(f"Creating Lakebase project {PROJECT_ID}")
    api.do(
        "POST",
        "/api/2.0/postgres/projects",
        query={"project_id": PROJECT_ID},
        body={"spec": {"display_name": "SNB Cash Ops", "pg_version": 17}},
    )
else:
    print(f"Project {PROJECT_ID} already exists")


def endpoint_active():
    ep = get_or_none(f"/api/2.0/postgres/{ENDPOINT}")
    if ep and ep.get("status", {}).get("current_state") == "ACTIVE":
        return ep
    return None


endpoint = wait_until(endpoint_active, "primary endpoint ACTIVE")
PGHOST = endpoint["status"]["hosts"]["host"]
print("PGHOST =", PGHOST)

# COMMAND ----------

# MAGIC %md ## 2. Writable table `public.dispatch_overrides`

# COMMAND ----------

import psycopg


def pg_connect():
    token = api.do("POST", "/api/2.0/postgres/credentials", body={"endpoint": ENDPOINT})["token"]
    user = w.current_user.me().user_name
    return psycopg.connect(
        host=PGHOST, port=5432, dbname=PG_DATABASE, user=user, password=token, sslmode="require", autocommit=True
    )


OVERRIDES_DDL = """
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
"""

with pg_connect() as conn:
    conn.execute(OVERRIDES_DDL)
    n = conn.execute("SELECT count(*) FROM public.dispatch_overrides").fetchone()[0]
print(f"public.dispatch_overrides ready ({n} rows)")

# COMMAND ----------

# MAGIC %md ## 3. Change Data Feed on `gold_route_stops`

# COMMAND ----------

route_stops_fqn = f"{CATALOG}.{SCHEMA}.gold_route_stops"
if table_exists(route_stops_fqn):
    props = {r["key"]: r["value"] for r in spark.sql(f"SHOW TBLPROPERTIES {route_stops_fqn}").collect()}
    if props.get("delta.enableChangeDataFeed", "false").lower() != "true":
        spark.sql(f"ALTER TABLE {route_stops_fqn} SET TBLPROPERTIES (delta.enableChangeDataFeed = true)")
        print("CDF enabled on gold_route_stops")
    else:
        print("CDF already enabled on gold_route_stops")
else:
    print("gold_route_stops does not exist yet — skipping CDF (ML task must run first)")

# COMMAND ----------

# MAGIC %md ## 4. Synced tables (SNAPSHOT)

# COMMAND ----------

synced_status = {}
for t in SYNCED_TABLES:
    target = f"{CATALOG}.{SCHEMA}.{t['name']}"
    source = f"{CATALOG}.{SCHEMA}.{t['source']}"
    if not table_exists(source):
        print(f"SKIP {target}: source {source} does not exist yet")
        synced_status[t["name"]] = "PENDING_SOURCE"
        continue

    existing = get_or_none(f"/api/2.0/postgres/synced_tables/{target}")
    if existing is None:
        print(f"Creating synced table {target} <- {source}")
        api.do(
            "POST",
            "/api/2.0/postgres/synced_tables",
            query={"synced_table_id": target},
            body={
                "spec": {
                    "source_table_full_name": source,
                    "primary_key_columns": t["pk"],
                    "scheduling_policy": "SNAPSHOT",
                    "branch": BRANCH,
                    "postgres_database": PG_DATABASE,
                    "create_database_objects_if_missing": True,
                    "new_pipeline_spec": {"storage_catalog": CATALOG, "storage_schema": SCHEMA},
                }
            },
        )
    else:
        pipeline_id = existing.get("status", {}).get("pipeline_id")
        if pipeline_id:
            print(f"Refreshing {target} via pipeline {pipeline_id}")
            try:
                w.pipelines.start_update(pipeline_id=pipeline_id, full_refresh=False)
            except Exception as e:
                print(f"  refresh not started ({e}); an update may already be running")

    def online(target=target):
        st = get_or_none(f"/api/2.0/postgres/synced_tables/{target}") or {}
        state = st.get("status", {}).get("detailed_state", "")
        if "FAILED" in state:
            raise RuntimeError(f"{target} failed: {st['status'].get('message')}")
        return state if state.startswith("SYNCED_TABLE_ONLINE") else None

    synced_status[t["name"]] = wait_until(online, f"{target} ONLINE", timeout_s=1800, every_s=20)

print(synced_status)

# COMMAND ----------

# MAGIC %md ## 5. Grants for the app

# COMMAND ----------

if not APP_SP_CLIENT_ID:
    try:
        app = w.apps.get(APP_NAME)
        APP_SP_CLIENT_ID = app.service_principal_client_id or ""
    except Exception as e:
        print(f"App {APP_NAME} not found ({e})")

if APP_SP_CLIENT_ID:
    grantee, identity_type = APP_SP_CLIENT_ID, "SERVICE_PRINCIPAL"
else:
    grantee, identity_type = FALLBACK_USER, "USER"
print(f"Granting {identity_type} {grantee}")

# Role IDs must start with a letter; SP application IDs often start with a digit.
raw_role = grantee.split("@")[0].replace(".", "-").replace("_", "-").lower()
role_id = raw_role if raw_role[:1].isalpha() else f"sp-{raw_role}"
roles = api.do("GET", f"/api/2.0/postgres/{BRANCH}/roles").get("roles", [])
if not any(r.get("status", {}).get("postgres_role") == grantee or r.get("spec", {}).get("postgres_role") == grantee for r in roles):
    api.do(
        "POST",
        f"/api/2.0/postgres/{BRANCH}/roles",
        query={"role_id": role_id},
        body={"spec": {"identity_type": identity_type, "postgres_role": grantee, "auth_method": "LAKEBASE_OAUTH_V1"}},
    )
    time.sleep(10)

GRANTS_SQL = f"""
GRANT CONNECT ON DATABASE {PG_DATABASE} TO "{grantee}";
GRANT USAGE ON SCHEMA public TO "{grantee}";
GRANT SELECT, INSERT, UPDATE, DELETE ON public.dispatch_overrides TO "{grantee}";
GRANT USAGE, SELECT ON SEQUENCE public.dispatch_overrides_override_id_seq TO "{grantee}";
GRANT USAGE ON SCHEMA {SCHEMA} TO "{grantee}";
GRANT SELECT ON ALL TABLES IN SCHEMA {SCHEMA} TO "{grantee}";
ALTER DEFAULT PRIVILEGES IN SCHEMA {SCHEMA} GRANT SELECT ON TABLES TO "{grantee}";
"""

with pg_connect() as conn:
    conn.execute(GRANTS_SQL)
    counts = {}
    for t in SYNCED_TABLES:
        exists = conn.execute(
            "SELECT to_regclass(%s) IS NOT NULL", (f"{SCHEMA}.{t['name']}",)
        ).fetchone()[0]
        counts[t["name"]] = conn.execute(f"SELECT count(*) FROM {SCHEMA}.{t['name']}").fetchone()[0] if exists else None

print("Postgres row counts:", counts)

# COMMAND ----------

dbutils.notebook.exit(
    str({"project": PROJECT_ID, "pghost": PGHOST, "synced": synced_status, "counts": counts, "grantee": grantee})
)
