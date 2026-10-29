# Databricks notebook source
# MAGIC %md
# MAGIC # SNB Forecast Scoring and Replenishment Orders
# MAGIC 1. Score the `champion` model for 2026-10-01..07 for every node. Features are built
# MAGIC    **recursively**: day-1 lags come from actual history, later days feed back predictions.
# MAGIC 2. Turn the 30-Sep cash position plus the P80 forecast into DELIVER / PICKUP orders for
# MAGIC    service date 2026-10-01 with priorities and time windows.

# COMMAND ----------

# MAGIC %pip install lightgbm==4.5.0 mlflow scikit-learn

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

dbutils.widgets.text("catalog", "stable_classic_nan_fe_vm_catalog")
dbutils.widgets.text("schema", "snb_cash_ops")
CATALOG, SCHEMA = dbutils.widgets.get("catalog"), dbutils.widgets.get("schema")
T = f"{CATALOG}.{SCHEMA}"
MODEL = f"{T}.cash_demand_forecast"

import json
import mlflow, numpy as np, pandas as pd
from mlflow.tracking import MlflowClient
from pyspark.sql import functions as F

SERVICE_DATE = pd.Timestamp("2026-10-01")
FEATURES = ["node_type", "dow", "dom", "is_weekend", "is_holiday", "is_payday",
            "lag_1", "lag_7", "lag_14", "roll7_mean", "roll28_mean"]
mlflow.set_registry_uri("databricks-uc")
model_version = str(MlflowClient().get_model_version_by_alias(MODEL, "champion").version)
model = mlflow.pyfunc.load_model(f"models:/{MODEL}@champion")
print(f"Loaded {MODEL} v{model_version} (@champion)")


def write(pdf, table, schema):
    sdf = spark.createDataFrame(pdf).select([F.col(c).cast(t).alias(c) for c, t in schema])
    sdf.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{T}.{table}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Recursive 7-day forecast
# MAGIC `silver_calendar` ends on 2026-09-30, so future calendar flags follow the same rules as
# MAGIC the history: ISO day-of-week (Mon=1), weekend = Sat/Sun, payday = day 1 or day >= 25.
# MAGIC No Thai public holidays fall on 1-7 October.

# COMMAND ----------

nodes = spark.table(f"{T}.gold_cash_nodes").toPandas()
hist = (spark.table(f"{T}.gold_node_daily").where("txn_date > DATE '2026-08-15' AND txn_date <= DATE '2026-09-30'")
        .select("node_id", "txn_date", "net_outflow_thb").toPandas().sort_values(["node_id", "txn_date"]))
series = {k: g.net_outflow_thb.astype(float).tolist()[-28:] for k, g in hist.groupby("node_id")}
missing = set(nodes.node_id) - set(series)
if missing:
    raise ValueError(f"{len(missing)} nodes have no history, e.g. {sorted(missing)[:5]}")

rows = []
for h in range(1, 8):
    d = SERVICE_DATE + pd.Timedelta(days=h - 1)
    feats = pd.DataFrame([{
        "node_type": str(n.node_type), "dow": int(d.dayofweek + 1), "dom": int(d.day),
        "is_weekend": bool(d.dayofweek >= 5), "is_holiday": False, "is_payday": bool(d.day == 1 or d.day >= 25),
        "lag_1": float(series[n.node_id][-1]), "lag_7": float(series[n.node_id][-7]),
        "lag_14": float(series[n.node_id][-14]),
        "roll7_mean": float(np.mean(series[n.node_id][-7:])), "roll28_mean": float(np.mean(series[n.node_id][-28:])),
    } for n in nodes.itertuples()])
    feats["dow"] = feats["dow"].astype(np.int32)
    feats["dom"] = feats["dom"].astype(np.int32)
    for c in ("is_weekend", "is_holiday", "is_payday"):
        feats[c] = feats[c].astype(bool)
    for c in ("lag_1", "lag_7", "lag_14", "roll7_mean", "roll28_mean"):
        feats[c] = feats[c].astype(np.float64)
    try:
        out = model.predict(feats[FEATURES])
    except Exception as schema_err:
        print(f"schema-enforced predict failed ({schema_err}); using inner python_model")
        out = model._model_impl.python_model.predict(None, feats[FEATURES])
    for n, p, q in zip(nodes.itertuples(), out.pred_net_outflow_thb, out.pred_p80_thb):
        rows.append((n.node_id, n.node_type, d.date(), h, float(p), float(max(p, q))))
        series[n.node_id].append(float(p))

forecast = pd.DataFrame(rows, columns=["node_id", "node_type", "forecast_date", "horizon_day",
                                       "pred_net_outflow_thb", "pred_p80_thb"])
forecast["model_name"], forecast["model_version"] = MODEL, model_version
forecast["scored_at"] = pd.Timestamp.now(tz="UTC").tz_localize(None)
write(forecast, "gold_demand_forecast", [
    ("node_id", "string"), ("node_type", "string"), ("forecast_date", "date"), ("horizon_day", "int"),
    ("pred_net_outflow_thb", "double"), ("pred_p80_thb", "double"), ("model_name", "string"),
    ("model_version", "string"), ("scored_at", "timestamp")])
print(f"gold_demand_forecast rows={len(forecast):,} nodes={forecast.node_id.nunique()} model v{model_version}")
print(forecast.groupby(["node_type", "horizon_day"]).pred_net_outflow_thb.mean().unstack().round(0).to_string())

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Replenishment orders for 2026-10-01
# MAGIC * `days_to_cashout = (current_cash - min_cash) / P80 daily forecast`
# MAGIC * **DELIVER** when days_to_cashout < 2.5: top up to min_cash + 5 days of P80, capped at capacity.
# MAGIC * **PICKUP** for RCMs/branches above 85% of capacity: collect the excess.
# MAGIC * Priority: CRITICAL < 1 day, HIGH < 2 days, else NORMAL.
# MAGIC * Windows: branches open..close, machines 08:00-18:00. Service 25 min branch, 15 min machine.

# COMMAND ----------

status = spark.table(f"{T}.gold_node_status").toPandas()
hours = nodes[["node_id", "open_min", "close_min"]]
day1 = forecast[forecast.horizon_day == 1][["node_id", "pred_p80_thb"]]
o = status.merge(day1, on="node_id").merge(hours, on="node_id")
o["days_to_cashout"] = (o.current_cash_thb - o.min_cash_thb) / o.pred_p80_thb.clip(lower=1000.0)
is_pickup = o.node_type.isin(["RCM", "BRANCH"]) & (o.current_cash_thb > 0.85 * o.capacity_thb)
is_deliver = (o.days_to_cashout < 2.5) & ~is_pickup
o = o[is_pickup | is_deliver].copy()
o["action"] = np.where(is_pickup[o.index], "PICKUP", "DELIVER")
deliver_amt = np.minimum(o.capacity_thb - o.current_cash_thb,
                         o.min_cash_thb + 5 * o.pred_p80_thb - o.current_cash_thb).clip(lower=0)
pickup_amt = (o.current_cash_thb - 0.85 * o.capacity_thb).clip(lower=0)
o["amount_thb"] = np.round(np.where(o.action == "DELIVER", deliver_amt, pickup_amt) / 1000) * 1000
o = o[o.amount_thb > 0].copy()
o["priority"] = np.where(o.action == "PICKUP", "NORMAL",
                         np.select([o.days_to_cashout < 1, o.days_to_cashout < 2], ["CRITICAL", "HIGH"], "NORMAL"))
branch = o.node_type == "BRANCH"
o["tw_start_min"] = np.where(branch, o.open_min, 480)
o["tw_end_min"] = np.where(branch, o.close_min, 1080)
o["service_min"] = np.where(branch, 25, 15)
o["service_date"] = SERVICE_DATE.date()
o = o.sort_values(["depot_id", "priority", "node_id"])
write(o, "gold_replenishment_orders", [
    ("service_date", "date"), ("node_id", "string"), ("node_type", "string"), ("node_name", "string"),
    ("depot_id", "string"), ("lat", "double"), ("lng", "double"), ("action", "string"), ("amount_thb", "double"),
    ("current_cash_thb", "double"), ("days_to_cashout", "double"), ("priority", "string"),
    ("tw_start_min", "int"), ("tw_end_min", "int"), ("service_min", "int")])

counts = o.groupby(["depot_id", "action", "priority"]).agg(orders=("node_id", "count"),
                                                            amount_mthb=("amount_thb", lambda s: round(s.sum() / 1e6, 2)))
print(f"TOTAL_ORDERS={len(o)}  DELIVER={int((o.action=='DELIVER').sum())}  PICKUP={int((o.action=='PICKUP').sum())}")
print(o.groupby("priority").size().to_string())
print(counts.to_string())
dbutils.notebook.exit(json.dumps({
    "forecast_rows": len(forecast), "model_version": model_version, "total_orders": len(o),
    "by_action": o.action.value_counts().to_dict(), "by_priority": o.priority.value_counts().to_dict(),
    "by_depot": o.depot_id.value_counts().to_dict(),
    "by_depot_action_priority": [dict(depot_id=k[0], action=k[1], priority=k[2], orders=int(v.orders), amount_mthb=float(v.amount_mthb))
                                 for k, v in counts.iterrows()]}))
