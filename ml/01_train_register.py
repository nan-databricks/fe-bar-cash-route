# Databricks notebook source
# MAGIC %md
# MAGIC # SNB Cash Demand Forecast — train and register
# MAGIC A single global model shares signal across branches, ATMs, and RCMs while
# MAGIC retaining node type as a categorical feature.  A P80 quantile model drives
# MAGIC conservative replenishment decisions.

# COMMAND ----------

# MAGIC %pip install lightgbm==4.5.0 mlflow
# COMMAND ----------
dbutils.library.restartPython()

# COMMAND ----------

dbutils.widgets.text("catalog", "stable_classic_nan_fe_vm_catalog")
dbutils.widgets.text("schema", "snb_cash_ops")
CATALOG, SCHEMA = dbutils.widgets.get("catalog"), dbutils.widgets.get("schema")
TABLE = f"{CATALOG}.{SCHEMA}"
MODEL_NAME = f"{TABLE}.cash_demand_forecast"
EXPERIMENT = "/Users/nan.chulpaibul@databricks.com/snb_cash_forecast"

import mlflow, lightgbm as lgb, numpy as np, pandas as pd
from mlflow.models import infer_signature
from mlflow.pyfunc import PythonModel
from mlflow.tracking import MlflowClient
from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, TimestampType

FEATURES = ["node_type", "dow", "dom", "is_weekend", "is_holiday", "is_payday",
            "lag_1", "lag_7", "lag_14", "roll7_mean", "roll28_mean"]
CATEGORICAL = ["node_type"]
TARGET = "net_outflow_thb"

def metric_rows(frame, prediction, baseline, segment):
    y = frame[TARGET].astype(float).to_numpy()
    denom = np.maximum(np.abs(y), 1.0)
    return [
        ("WAPE_model", float(np.abs(y - prediction).sum() / denom.sum()), segment),
        ("MAPE_model", float((np.abs(y - prediction) / denom).mean()), segment),
        ("WAPE_naive", float(np.abs(y - baseline).sum() / denom.sum()), segment),
        ("MAPE_naive", float((np.abs(y - baseline) / denom).mean()), segment),
    ]

class DemandForecastModel(PythonModel):
    """MLflow pyfunc returning point and P80 forecasts from contract feature rows."""
    def __init__(self, point_model, p80_model):
        self.point_model, self.p80_model = point_model, p80_model
    def predict(self, context, model_input, params=None):
        x = model_input[FEATURES].copy()
        x["node_type"] = x["node_type"].astype("category")
        pred = self.point_model.predict(x)
        p80 = np.maximum(pred, self.p80_model.predict(x))
        return pd.DataFrame({"pred_net_outflow_thb": pred, "pred_p80_thb": p80})

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load the frozen feature contract and make a time-based holdout

# COMMAND ----------

pdf = spark.table(f"{TABLE}.gold_demand_features").toPandas()
pdf["txn_date"] = pd.to_datetime(pdf["txn_date"])
for col in FEATURES:
    if col != "node_type":
        pdf[col] = pd.to_numeric(pdf[col], errors="coerce")
pdf = pdf.dropna(subset=FEATURES + [TARGET]).copy()
pdf["node_type"] = pdf["node_type"].astype("category")
train = pdf[pdf.txn_date < "2026-08-01"].copy()
valid = pdf[(pdf.txn_date >= "2026-08-01") & (pdf.txn_date <= "2026-09-30")].copy()
if train.empty or valid.empty:
    raise ValueError("Training or validation split is empty; gold_demand_features is incomplete.")
print(f"Training rows={len(train):,}, validation rows={len(valid):,}, nodes={pdf.node_id.nunique():,}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Fit point and P80 LightGBM models, then compare to the lag/rolling baseline

# COMMAND ----------

params = dict(learning_rate=0.05, num_leaves=48, min_child_samples=40,
              subsample=0.85, colsample_bytree=0.9, n_estimators=500,
              random_state=42, verbosity=-1)
point = lgb.LGBMRegressor(objective="regression_l1", **params)
p80 = lgb.LGBMRegressor(objective="quantile", alpha=0.8, **params)
point.fit(train[FEATURES], train[TARGET], categorical_feature=CATEGORICAL,
          callbacks=[lgb.early_stopping(40, verbose=False)],
          eval_set=[(valid[FEATURES], valid[TARGET])])
p80.fit(train[FEATURES], train[TARGET], categorical_feature=CATEGORICAL,
        callbacks=[lgb.early_stopping(40, verbose=False)],
        eval_set=[(valid[FEATURES], valid[TARGET])])
pred = point.predict(valid[FEATURES])
baseline = valid["lag_7"].fillna(valid["roll28_mean"]).fillna(0).to_numpy()
metrics = metric_rows(valid, pred, baseline, "ALL")
for node_type, group in valid.assign(_pred=pred, _base=baseline).groupby("node_type", observed=True):
    metrics += metric_rows(group, group._pred.to_numpy(), group._base.to_numpy(), str(node_type))
metrics_pdf = pd.DataFrame(metrics, columns=["metric", "value", "segment"])
print(metrics_pdf.pivot(index="segment", columns="metric", values="value").round(4).to_string())

# COMMAND ----------

# MAGIC %md
# MAGIC ## Log the dual-model pyfunc, register it in Unity Catalog, and promote champion

# COMMAND ----------

mlflow.set_experiment(EXPERIMENT)
mlflow.set_registry_uri("databricks-uc")
example = valid[FEATURES].head(3).copy()
with mlflow.start_run(run_name="snb_global_lgb_forecast") as run:
    mlflow.log_params({"train_cutoff": "2026-08-01", "validation_end": "2026-09-30",
                       "features": ",".join(FEATURES), "model_strategy": "global_lightgbm"})
    for row in metrics_pdf.itertuples(index=False):
        mlflow.log_metric(f"{row.metric}_{row.segment}", float(row.value))
    wrapped = DemandForecastModel(point, p80)
    output_example = wrapped.predict(None, example)
    model_info = mlflow.pyfunc.log_model(
        artifact_path="forecast_model", python_model=wrapped,
        input_example=example, signature=infer_signature(example, output_example),
        pip_requirements=["mlflow", "lightgbm==4.5.0", "pandas", "numpy"])
    run_id = run.info.run_id
registered = mlflow.register_model(f"runs:/{run_id}/forecast_model", MODEL_NAME)
client = MlflowClient()
client.set_registered_model_alias(MODEL_NAME, "champion", registered.version)
print(f"MLFLOW_RUN_ID={run_id}")
print(f"MODEL_NAME={MODEL_NAME}")
print(f"MODEL_VERSION={registered.version}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Persist contract metrics for the dashboard and evidence

# COMMAND ----------

now = pd.Timestamp.utcnow().to_pydatetime()
metrics_pdf["model_version"] = str(registered.version)
metrics_pdf["logged_at"] = now
metrics_sdf = spark.createDataFrame(metrics_pdf[["model_version", "metric", "value", "segment", "logged_at"]])
metrics_sdf.write.mode("overwrite").saveAsTable(f"{TABLE}.gold_model_metrics")
print("METRICS_TABLE")
print(metrics_pdf[["segment", "metric", "value"]].sort_values(["segment", "metric"]).to_string(index=False))
