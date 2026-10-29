# Databricks notebook source
# MAGIC %md
# MAGIC # SNB Cash Forecast Serving Endpoint
# MAGIC Idempotently reconciles the endpoint to the UC model alias `champion`, then
# MAGIC queries a feature row to prove the online serving contract.

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

import json, time, mlflow
from datetime import timedelta
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import EndpointCoreConfigInput, ServedEntityInput

mlflow.set_registry_uri("databricks-uc")
champion_version = str(mlflow.tracking.MlflowClient().get_model_version_by_alias(MODEL_NAME, "champion").version)
w = WorkspaceClient()
sample = (spark.table(f"{CATALOG}.{SCHEMA}.gold_demand_features")
          .where("txn_date >= DATE '2026-09-20'")
          .select("node_type", "dow", "dom", "is_weekend", "is_holiday", "is_payday",
                  "lag_1", "lag_7", "lag_14", "roll7_mean", "roll28_mean")
          .dropna().limit(1).toPandas().to_dict(orient="records"))
if not sample:
    raise ValueError("No valid feature row available for endpoint smoke test.")
for row in sample:
    for k, v in row.items():
        if hasattr(v, "item"):
            row[k] = v.item()

config = EndpointCoreConfigInput(
    served_entities=[ServedEntityInput(
        name="cash-demand-forecast-champion",
        entity_name=MODEL_NAME,
        entity_version=champion_version,
        workload_size="Small",
        scale_to_zero_enabled=True,
    )]
)
try:
    existing = w.serving_endpoints.get(ENDPOINT)
    print(f"Updating existing endpoint {ENDPOINT}, current_state={existing.state}")
    w.serving_endpoints.update_config_and_wait(name=ENDPOINT, served_entities=config.served_entities, timeout=timedelta(minutes=30))
except Exception as exc:
    if "RESOURCE_DOES_NOT_EXIST" not in str(exc) and "does not exist" not in str(exc).lower():
        raise
    print(f"Creating endpoint {ENDPOINT}")
    w.serving_endpoints.create_and_wait(name=ENDPOINT, config=config, timeout=timedelta(minutes=30))

# COMMAND ----------

deadline = time.time() + 30 * 60
while time.time() < deadline:
    endpoint = w.serving_endpoints.get(ENDPOINT)
    state = str(endpoint.state)
    print(f"endpoint_state={state}")
    if "READY" in state:
        break
    if "FAILED" in state:
        raise RuntimeError(f"Endpoint failed: {endpoint}")
    time.sleep(20)
else:
    raise TimeoutError("Endpoint did not become READY within 30 minutes.")

response = w.serving_endpoints.query(name=ENDPOINT, dataframe_records=sample)
print("ENDPOINT_STATE=READY")
print("SAMPLE_REQUEST_JSON=" + json.dumps({"dataframe_records": sample}, default=str))
print("SAMPLE_RESPONSE_JSON=" + json.dumps(response.as_dict(), default=str))
