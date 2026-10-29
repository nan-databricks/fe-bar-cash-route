# Databricks notebook source
# MAGIC %md
# MAGIC # SNB Cash Forecast — Model Serving endpoint
# MAGIC Idempotently creates or updates `snb-cash-forecast` so it serves the UC model version
# MAGIC behind alias `champion` (Small, scale-to-zero), waits for READY, then sends one real
# MAGIC feature row to prove the online contract the app uses.

# COMMAND ----------

# MAGIC %pip install databricks-sdk mlflow

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

dbutils.widgets.text("catalog", "stable_classic_nan_fe_vm_catalog")
dbutils.widgets.text("schema", "snb_cash_ops")
CATALOG, SCHEMA = dbutils.widgets.get("catalog"), dbutils.widgets.get("schema")
MODEL_NAME = f"{CATALOG}.{SCHEMA}.cash_demand_forecast"
ENDPOINT = "snb-cash-forecast"

import json, time
from datetime import timedelta
import mlflow
from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import NotFound
from databricks.sdk.service.serving import EndpointCoreConfigInput, ServedEntityInput

mlflow.set_registry_uri("databricks-uc")
version = str(mlflow.tracking.MlflowClient().get_model_version_by_alias(MODEL_NAME, "champion").version)
print(f"champion = {MODEL_NAME} v{version}")
w = WorkspaceClient()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Create or update the endpoint

# COMMAND ----------

entities = [ServedEntityInput(name="cash-demand-forecast", entity_name=MODEL_NAME, entity_version=version,
                              workload_size="Small", scale_to_zero_enabled=True)]
try:
    current = w.serving_endpoints.get(ENDPOINT)
    served = [(e.entity_name, e.entity_version) for e in (current.config.served_entities or [])] if current.config else []
    if served == [(MODEL_NAME, version)] and current.state and str(current.state.config_update) not in ("ConfigUpdate.IN_PROGRESS",):
        print(f"Endpoint already serves v{version}; no update needed")
    else:
        print(f"Updating {ENDPOINT}: {served} -> v{version}")
        w.serving_endpoints.update_config_and_wait(name=ENDPOINT, served_entities=entities, timeout=timedelta(minutes=40))
except NotFound:
    print(f"Creating {ENDPOINT}")
    w.serving_endpoints.create_and_wait(name=ENDPOINT, config=EndpointCoreConfigInput(served_entities=entities),
                                        timeout=timedelta(minutes=40))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Wait until READY and query with a real feature row

# COMMAND ----------

deadline = time.time() + 30 * 60
while True:
    ep = w.serving_endpoints.get(ENDPOINT)
    ready, upd = str(ep.state.ready), str(ep.state.config_update)
    print(f"state.ready={ready} config_update={upd}")
    if ready.endswith("READY") and not ready.endswith("NOT_READY") and "IN_PROGRESS" not in upd:
        break
    if "FAILED" in upd or time.time() > deadline:
        raise RuntimeError(f"Endpoint not ready: {ep.state}")
    time.sleep(20)

rows = (spark.table(f"{CATALOG}.{SCHEMA}.gold_demand_features")
        .where("txn_date = DATE '2026-09-30'")
        .select("node_id", "node_type", "dow", "dom", "is_weekend", "is_holiday", "is_payday",
                "lag_1", "lag_7", "lag_14", "roll7_mean", "roll28_mean", "net_outflow_thb")
        .dropna().orderBy("node_id").limit(3).toPandas())
records = rows.drop(columns=["node_id", "net_outflow_thb"]).to_dict(orient="records")
records = [{k: (v.item() if hasattr(v, "item") else v) for k, v in r.items()} for r in records]
resp = w.serving_endpoints.query(name=ENDPOINT, dataframe_records=records).as_dict()
print(f"ENDPOINT={ENDPOINT} STATE=READY SERVED={MODEL_NAME} v{version}")
print("REQUEST_JSON=" + json.dumps({"dataframe_records": records}))
print("RESPONSE_JSON=" + json.dumps(resp, default=str))
print("ACTUALS=" + json.dumps(dict(zip(rows.node_id, rows.net_outflow_thb.astype(float)))))
dbutils.notebook.exit(json.dumps({"endpoint": ENDPOINT, "state": "READY", "version": version,
                                  "request": {"dataframe_records": records}, "response": resp,
                                  "node_ids": rows.node_id.tolist(), "actuals": rows.net_outflow_thb.astype(float).tolist()}, default=str))
