# Databricks notebook source
# MAGIC %md
# MAGIC # SNB Forecast Scoring and Replenishment Orders
# MAGIC Scores the registered champion for seven days using recursive lag updates, then
# MAGIC converts the first-day risk position into delivery and pickup orders.

# COMMAND ----------

# MAGIC %pip install lightgbm==4.5.0 mlflow
# COMMAND ----------
dbutils.library.restartPython()

# COMMAND ----------

dbutils.widgets.text("catalog", "stable_classic_nan_fe_vm_catalog")
dbutils.widgets.text("schema", "snb_cash_ops")
CATALOG, SCHEMA = dbutils.widgets.get("catalog"), dbutils.widgets.get("schema")
T = f"{CATALOG}.{SCHEMA}"
MODEL = f"{T}.cash_demand_forecast"

import mlflow, pandas as pd, numpy as np
from datetime import datetime
from mlflow.tracking import MlflowClient
SERVICE_DATE = pd.Timestamp("2026-10-01")

FEATURES = ["node_type", "dow", "dom", "is_weekend", "is_holiday", "is_payday",
            "lag_1", "lag_7", "lag_14", "roll7_mean", "roll28_mean"]
client = MlflowClient()
model_version = client.get_model_version_by_alias(MODEL, "champion").version
model = mlflow.pyfunc.load_model(f"models:/{MODEL}@champion")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Construct future feature rows with the last observed cash outflow history

# COMMAND ----------

nodes = spark.table(f"{T}.gold_cash_nodes").toPandas()
history = spark.table(f"{T}.gold_node_daily").where("txn_date <= DATE '2026-09-30'").toPandas()
calendar = spark.table(f"{T}.silver_calendar").where("cal_date BETWEEN DATE '2026-10-01' AND DATE '2026-10-07'").toPandas()
history["txn_date"] = pd.to_datetime(history["txn_date"])
calendar["cal_date"] = pd.to_datetime(calendar["cal_date"])
cal = calendar.set_index("cal_date").to_dict("index")
series = {node_id: group.sort_values("txn_date")["net_outflow_thb"].astype(float).tail(28).tolist()
          for node_id, group in history.groupby("node_id")}
if len(series) != len(nodes):
    raise ValueError("Node history is incomplete; do not score until pipeline gold tables are complete.")

rows = []
for day in range(1, 8):
    forecast_date = SERVICE_DATE + pd.Timedelta(days=day - 1)
    c = cal.get(forecast_date, {})
    input_rows, node_ids = [], []
    for node in nodes.itertuples(index=False):
        hist = series[node.node_id]
        input_rows.append({
            "node_type": node.node_type, "dow": int(c.get("dow", forecast_date.dayofweek)),
            "dom": int(forecast_date.day), "is_weekend": bool(c.get("is_weekend", forecast_date.dayofweek >= 5)),
            "is_holiday": bool(c.get("is_holiday", False)), "is_payday": bool(c.get("is_payday", False)),
            "lag_1": hist[-1], "lag_7": hist[-7], "lag_14": hist[-14],
            "roll7_mean": float(np.mean(hist[-7:])), "roll28_mean": float(np.mean(hist[-28:])),
        })
        node_ids.append(node.node_id)
    features = pd.DataFrame(input_rows)[FEATURES]
    scored = model.predict(features)
    for node_id, p, q in zip(node_ids, scored["pred_net_outflow_thb"], scored["pred_p80_thb"]):
        rows.append({"node_id": node_id, "forecast_date": forecast_date.date(), "horizon_day": day,
                     "pred_net_outflow_thb": float(p), "pred_p80_thb": float(max(p, q))})
        series[node_id].append(float(p))
forecast = pd.DataFrame(rows).merge(nodes[["node_id", "node_type"]], on="node_id")
forecast["model_name"], forecast["model_version"], forecast["scored_at"] = MODEL, str(model_version), datetime.utcnow()
forecast = forecast[["node_id", "node_type", "forecast_date", "horizon_day", "pred_net_outflow_thb",
                     "pred_p80_thb", "model_name", "model_version", "scored_at"]]
spark.createDataFrame(forecast).write.mode("overwrite").saveAsTable(f"{T}.gold_demand_forecast")
print(f"FORECAST_ROWS={len(forecast):,}; MODEL_VERSION={model_version}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create 1 October delivery/pickup orders from cash position and P80 demand

# COMMAND ----------

status = spark.table(f"{T}.gold_node_status").toPandas()
day1 = forecast[forecast.horizon_day == 1][["node_id", "pred_net_outflow_thb", "pred_p80_thb"]]
orders = status.merge(day1, on="node_id", how="inner")
daily = np.maximum(orders.pred_p80_thb, 1.0)
orders["days_to_cashout"] = (orders.current_cash_thb - orders.min_cash_thb) / daily
deliver = orders.days_to_cashout < 2.5
pickup = orders.node_type.isin(["RCM", "BRANCH"]) & (orders.current_cash_thb > orders.capacity_thb * .85)
orders = orders[deliver | pickup].copy()
orders["action"] = np.where(pickup.loc[orders.index], "PICKUP", "DELIVER")
orders["amount_thb"] = np.where(
    orders.action.eq("DELIVER"),
    np.minimum(orders.capacity_thb - orders.current_cash_thb,
               np.maximum(0, orders.min_cash_thb + 5 * orders.pred_p80_thb - orders.current_cash_thb)),
    np.maximum(0, orders.current_cash_thb - orders.capacity_thb * .85),
)
orders = orders[orders.amount_thb > 0].copy()
orders["priority"] = np.select([orders.days_to_cashout < 1, orders.days_to_cashout < 2],
                               ["CRITICAL", "HIGH"], default="NORMAL")
orders["tw_start_min"] = np.where(orders.node_type.eq("BRANCH"), orders.open_min, 480).astype(int)
orders["tw_end_min"] = np.where(orders.node_type.eq("BRANCH"), orders.close_min, 1080).astype(int)
orders["service_min"] = np.where(orders.node_type.eq("BRANCH"), 25, 15).astype(int)
orders["service_date"] = SERVICE_DATE.date()
order_cols = ["service_date", "node_id", "node_type", "node_name", "depot_id", "lat", "lng", "action",
              "amount_thb", "current_cash_thb", "days_to_cashout", "priority", "tw_start_min", "tw_end_min", "service_min"]
orders = orders[order_cols]
spark.createDataFrame(orders).write.mode("overwrite").saveAsTable(f"{T}.gold_replenishment_orders")
print("ORDER_COUNTS")
print(orders.groupby(["action", "priority", "depot_id"]).size().reset_index(name="orders").to_string(index=False))
print(f"TOTAL_ORDERS={len(orders)}")
