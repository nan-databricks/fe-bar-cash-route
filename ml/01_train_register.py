# Databricks notebook source
# MAGIC %md
# MAGIC # SNB Cash Demand Forecast — train and register
# MAGIC One **global LightGBM** model shares signal across 679 branches, ATMs and RCMs, with
# MAGIC `node_type` as a categorical feature. A second LightGBM with quantile loss (alpha 0.8)
# MAGIC gives a P80 forecast used for conservative replenishment. Both are wrapped in one
# MAGIC MLflow pyfunc, registered in Unity Catalog and promoted to alias `champion`.

# COMMAND ----------

# MAGIC %pip install lightgbm==4.5.0 ortools==9.11.4210 mlflow scikit-learn

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

dbutils.widgets.text("catalog", "stable_classic_nan_fe_vm_catalog")
dbutils.widgets.text("schema", "snb_cash_ops")
CATALOG, SCHEMA = dbutils.widgets.get("catalog"), dbutils.widgets.get("schema")
T = f"{CATALOG}.{SCHEMA}"
MODEL_NAME = f"{T}.cash_demand_forecast"
EXPERIMENT = "/Users/nan.chulpaibul@databricks.com/snb_cash_forecast"

import cloudpickle, lightgbm as lgb, mlflow, numpy as np, pandas as pd, sklearn
from mlflow.models import infer_signature
from mlflow.pyfunc import PythonModel
from mlflow.tracking import MlflowClient
from pyspark.sql import functions as F

FEATURES = ["node_type", "dow", "dom", "is_weekend", "is_holiday", "is_payday",
            "lag_1", "lag_7", "lag_14", "roll7_mean", "roll28_mean"]
BOOL_COLS = ["is_weekend", "is_holiday", "is_payday"]
NODE_TYPES = ["ATM", "BRANCH", "RCM"]
TARGET = "net_outflow_thb"


def prepare(frame):
    """Contract feature rows -> LightGBM matrix (shared by training and the pyfunc)."""
    x = frame[FEATURES].copy()
    x["node_type"] = pd.Categorical(x["node_type"].astype(str), categories=NODE_TYPES)
    for c in BOOL_COLS:
        x[c] = x[c].astype(str).str.lower().isin(["true", "1"]).astype(int)
    for c in FEATURES:
        if c != "node_type":
            x[c] = pd.to_numeric(x[c], errors="coerce").astype(float)
    return x


class DemandForecastModel(PythonModel):
    """Returns pred_net_outflow_thb (median) and pred_p80_thb for contract feature rows."""
    def __init__(self, point_model, p80_model):
        self.point_model, self.p80_model = point_model, p80_model

    def predict(self, context, model_input, params=None):
        x = prepare(model_input)
        pred = self.point_model.predict(x)
        p80 = np.maximum(pred, self.p80_model.predict(x))
        return pd.DataFrame({"pred_net_outflow_thb": pred, "pred_p80_thb": p80})


def metric_rows(y, pred, base, segment):
    y = np.asarray(y, float)
    denom = np.maximum(np.abs(y), 1.0)
    return [
        ("WAPE_model", float(np.abs(y - pred).sum() / np.abs(y).sum()), segment),
        ("WAPE_naive", float(np.abs(y - base).sum() / np.abs(y).sum()), segment),
        ("MAPE_model", float(np.mean(np.abs(y - pred) / denom)), segment),
        ("MAPE_naive", float(np.mean(np.abs(y - base) / denom)), segment),
    ]

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Load features and make a time-based split
# MAGIC Train on everything before 2026-08-01; validate on 2026-08-01 .. 2026-09-30 (two months
# MAGIC that include two payday cycles). Rows without a full 14-day lag history are dropped.

# COMMAND ----------

pdf = spark.table(f"{T}.gold_demand_features").toPandas()
pdf["txn_date"] = pd.to_datetime(pdf["txn_date"])
pdf = pdf.dropna(subset=FEATURES + [TARGET]).reset_index(drop=True)
train = pdf[pdf.txn_date < "2026-08-01"]
valid = pdf[(pdf.txn_date >= "2026-08-01") & (pdf.txn_date <= "2026-09-30")]
X_tr, X_va = prepare(train), prepare(valid)
y_tr, y_va = train[TARGET].astype(float), valid[TARGET].astype(float)
print(f"train rows={len(train):,}  valid rows={len(valid):,}  nodes={pdf.node_id.nunique()}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Fit point (L1) and P80 (quantile) models; compare to the naive baseline
# MAGIC Naive baseline = same weekday last week (`lag_7`), falling back to `roll28_mean`.

# COMMAND ----------

params = dict(learning_rate=0.05, num_leaves=63, min_child_samples=50, subsample=0.85,
              subsample_freq=1, colsample_bytree=0.9, n_estimators=600, random_state=42, verbosity=-1)
point = lgb.LGBMRegressor(objective="regression_l1", **params)
p80 = lgb.LGBMRegressor(objective="quantile", alpha=0.8, **params)
point.fit(X_tr, y_tr, eval_set=[(X_va, y_va)], callbacks=[lgb.early_stopping(50, verbose=False)])
p80.fit(X_tr, y_tr, eval_set=[(X_va, y_va)], callbacks=[lgb.early_stopping(50, verbose=False)])

pred = point.predict(X_va)
p80_pred = np.maximum(pred, p80.predict(X_va))
base = valid["lag_7"].fillna(valid["roll28_mean"]).astype(float).to_numpy()
metrics = metric_rows(y_va, pred, base, "ALL")
for nt in NODE_TYPES:
    m = (valid.node_type == nt).to_numpy()
    if m.any():
        metrics += metric_rows(y_va[m], pred[m], base[m], nt)
coverage = float(np.mean(y_va.to_numpy() <= p80_pred))
metrics.append(("P80_coverage", coverage, "ALL"))
metrics_pdf = pd.DataFrame(metrics, columns=["metric", "value", "segment"])
print(f"best_iteration point={point.best_iteration_}  p80={p80.best_iteration_}")
print(metrics_pdf.pivot(index="segment", columns="metric", values="value").round(4).to_string())

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Log the dual-model pyfunc, register to Unity Catalog, alias `champion`

# COMMAND ----------

mlflow.set_registry_uri("databricks-uc")
mlflow.set_experiment(EXPERIMENT)
example = valid[FEATURES].head(3).copy()
example["node_type"] = example["node_type"].astype(str)
for c in BOOL_COLS:
    example[c] = example[c].astype(bool)
wrapped = DemandForecastModel(point, p80)
signature = infer_signature(example, wrapped.predict(None, example))
reqs = [f"mlflow=={mlflow.__version__}", "lightgbm==4.5.0", f"scikit-learn=={sklearn.__version__}",
        f"pandas=={pd.__version__}", f"numpy=={np.__version__}", f"cloudpickle=={cloudpickle.__version__}"]

with mlflow.start_run(run_name="snb_global_lgb_forecast") as run:
    mlflow.log_params({"train_end_exclusive": "2026-08-01", "valid_window": "2026-08-01..2026-09-30",
                       "features": ",".join(FEATURES), "strategy": "global LightGBM L1 + quantile 0.8",
                       "best_iter_point": point.best_iteration_, "best_iter_p80": p80.best_iteration_})
    for r in metrics_pdf.itertuples(index=False):
        mlflow.log_metric(f"{r.metric}_{r.segment}", r.value)
    mlflow.pyfunc.log_model(artifact_path="forecast_model", python_model=wrapped, signature=signature,
                            input_example=example, pip_requirements=reqs)
    run_id = run.info.run_id

mv = mlflow.register_model(f"runs:/{run_id}/forecast_model", MODEL_NAME)
MlflowClient().set_registered_model_alias(MODEL_NAME, "champion", mv.version)
print(f"MLFLOW_RUN_ID={run_id}")
print(f"MODEL={MODEL_NAME}  VERSION={mv.version}  ALIAS=champion")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Persist metrics to `gold_model_metrics`

# COMMAND ----------

metrics_pdf["model_version"] = str(mv.version)
metrics_pdf["logged_at"] = pd.Timestamp.now(tz="UTC").tz_localize(None)
(spark.createDataFrame(metrics_pdf)
 .select(F.col("model_version").cast("string"), F.col("metric").cast("string"), F.col("value").cast("double"),
         F.col("segment").cast("string"), F.col("logged_at").cast("timestamp"))
 .write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{T}.gold_model_metrics"))

w = metrics_pdf.pivot(index="segment", columns="metric", values="value")
print("METRICS_TABLE (validation 2026-08-01..2026-09-30)")
print(f"{'segment':8} {'WAPE_model':>10} {'WAPE_naive':>10} {'MAPE_model':>10} {'MAPE_naive':>10}")
for seg in ["ALL"] + NODE_TYPES:
    if seg in w.index:
        r = w.loc[seg]
        print(f"{seg:8} {r.WAPE_model:10.4f} {r.WAPE_naive:10.4f} {r.MAPE_model:10.4f} {r.MAPE_naive:10.4f}")
print(f"P80 coverage (share of actuals <= p80): {coverage:.3f}")
dbutils.notebook.exit(f"run_id={run_id};version={mv.version};wape_model={w.loc['ALL','WAPE_model']:.4f};wape_naive={w.loc['ALL','WAPE_naive']:.4f}")
