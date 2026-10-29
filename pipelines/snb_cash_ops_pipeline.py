# Databricks notebook source
# Lakeflow Spark Declarative Pipelines for the synthetic SNB cash-operations demo.
from pyspark import pipelines as dp
from pyspark.sql import functions as F
from pyspark.sql.window import Window

CATALOG = spark.conf.get("spark.databricks.pipeline.catalog", "stable_classic_nan_fe_vm_catalog")
SCHEMA = spark.conf.get("spark.databricks.pipeline.target", "snb_cash_ops")
RAW = f"/Volumes/{CATALOG}/{SCHEMA}/raw"

BRONZE_COMMENT = "Bronze Auto Loader ingestion of synthetic SNB cash logistics CSV data."
SILVER_COMMENT = "Silver typed and quality-checked synthetic SNB cash logistics data."
GOLD_PROPERTIES = {"delta.enableChangeDataFeed": "true", "quality": "gold"}

def cloudfiles(entity):
    return (spark.readStream.format("cloudFiles")
            .option("cloudFiles.format", "csv")
            .option("header", "true")
            .option("cloudFiles.inferColumnTypes", "true")
            .load(f"{RAW}/{entity}")
            .withColumn("_ingested_at", F.current_timestamp())
            .withColumn("_source_file", F.col("_metadata.file_path")))

def bronze(entity):
    @dp.table(name=f"bronze_{entity}", comment=f"{BRONZE_COMMENT} Source entity: {entity}.",
              table_properties={"quality": "bronze"})
    def table():
        return cloudfiles(entity)
    return table

for _entity in ["depots", "vehicles", "branches", "machines", "calendar",
                "machine_daily", "branch_daily", "cit_trips"]:
    bronze(_entity)

# COMMAND ----------

def typed(source, casts):
    return spark.readStream.table(source).select(*[
        F.col(name).cast(data_type).alias(name) for name, data_type in casts
    ])

@dp.expect_or_drop("valid_depot_id", "depot_id IS NOT NULL")
@dp.expect("thai_coordinates_warning", "lat BETWEEN 5 AND 21 AND lng BETWEEN 97 AND 106")
@dp.table(name="silver_depots", comment=SILVER_COMMENT, table_properties={"quality": "silver"})
def silver_depots():
    return typed("bronze_depots", [("depot_id", "string"), ("depot_name", "string"), ("district", "string"),
        ("lat", "double"), ("lng", "double"), ("vault_capacity_thb", "double")])

@dp.expect_or_drop("valid_vehicle_id", "vehicle_id IS NOT NULL AND depot_id IS NOT NULL")
@dp.expect_or_drop("positive_capacity", "cash_capacity_thb >= 0 AND cost_per_km_thb >= 0")
@dp.table(name="silver_vehicles", comment=SILVER_COMMENT + " Custodian fields are PII and governed by a UC mask.",
          table_properties={"quality": "silver"})
def silver_vehicles():
    return typed("bronze_vehicles", [("vehicle_id", "string"), ("depot_id", "string"), ("vehicle_type", "string"),
        ("cash_capacity_thb", "double"), ("cost_per_km_thb", "double"), ("crew_size", "int"),
        ("custodian_name", "string"), ("custodian_phone", "string")])

@dp.expect_or_drop("valid_branch_id", "branch_id IS NOT NULL AND depot_id IS NOT NULL")
@dp.expect_or_drop("nonnegative_cash", "vault_capacity_thb >= 0 AND min_cash_thb >= 0")
@dp.expect("thai_coordinates_warning", "lat BETWEEN 5 AND 21 AND lng BETWEEN 97 AND 106")
@dp.table(name="silver_branches", comment=SILVER_COMMENT, table_properties={"quality": "silver"})
def silver_branches():
    return typed("bronze_branches", [("branch_id", "string"), ("branch_name", "string"), ("district", "string"),
        ("depot_id", "string"), ("lat", "double"), ("lng", "double"), ("vault_capacity_thb", "double"),
        ("min_cash_thb", "double"), ("open_min", "int"), ("close_min", "int")])

@dp.expect_or_drop("valid_machine_id", "machine_id IS NOT NULL AND depot_id IS NOT NULL")
@dp.expect_or_drop("nonnegative_cash", "cassette_capacity_thb >= 0 AND min_cash_thb >= 0")
@dp.expect("thai_coordinates_warning", "lat BETWEEN 5 AND 21 AND lng BETWEEN 97 AND 106")
@dp.table(name="silver_machines", comment=SILVER_COMMENT, table_properties={"quality": "silver"})
def silver_machines():
    return typed("bronze_machines", [("machine_id", "string"), ("machine_type", "string"), ("site_name", "string"),
        ("district", "string"), ("depot_id", "string"), ("lat", "double"), ("lng", "double"),
        ("cassette_capacity_thb", "double"), ("min_cash_thb", "double")])

@dp.expect_or_drop("valid_calendar_date", "cal_date IS NOT NULL")
@dp.table(name="silver_calendar", comment=SILVER_COMMENT, table_properties={"quality": "silver"})
def silver_calendar():
    return typed("bronze_calendar", [("cal_date", "date"), ("dow", "int"), ("is_weekend", "boolean"),
        ("is_holiday", "boolean"), ("holiday_name", "string"), ("is_payday", "boolean")])

@dp.expect_or_drop("valid_machine_daily_key", "machine_id IS NOT NULL AND txn_date IS NOT NULL")
@dp.expect_or_drop("nonnegative_amounts", "withdrawals_thb >= 0 AND deposits_thb >= 0 AND replenished_thb >= 0 AND closing_cash_thb >= 0")
@dp.table(name="silver_machine_daily", comment=SILVER_COMMENT, table_properties={"quality": "silver"})
def silver_machine_daily():
    return typed("bronze_machine_daily", [("machine_id", "string"), ("txn_date", "date"), ("withdrawals_thb", "double"),
        ("deposits_thb", "double"), ("replenished_thb", "double"), ("closing_cash_thb", "double"), ("cash_out_flag", "boolean")])

@dp.expect_or_drop("valid_branch_daily_key", "branch_id IS NOT NULL AND txn_date IS NOT NULL")
@dp.expect_or_drop("nonnegative_amounts", "inflow_thb >= 0 AND outflow_thb >= 0 AND delivered_thb >= 0 AND collected_thb >= 0 AND closing_vault_thb >= 0")
@dp.table(name="silver_branch_daily", comment=SILVER_COMMENT, table_properties={"quality": "silver"})
def silver_branch_daily():
    return typed("bronze_branch_daily", [("branch_id", "string"), ("txn_date", "date"), ("inflow_thb", "double"),
        ("outflow_thb", "double"), ("delivered_thb", "double"), ("collected_thb", "double"), ("closing_vault_thb", "double")])

@dp.expect_or_drop("valid_trip_key", "trip_id IS NOT NULL AND service_date IS NOT NULL AND depot_id IS NOT NULL")
@dp.expect_or_drop("nonnegative_trip_metrics", "stops >= 0 AND km >= 0 AND duration_min >= 0 AND cost_thb >= 0")
@dp.table(name="silver_cit_trips", comment=SILVER_COMMENT + " A governed view applies depot row filtering.",
          table_properties={"quality": "silver"})
def silver_cit_trips():
    return typed("bronze_cit_trips", [("trip_id", "string"), ("service_date", "date"), ("depot_id", "string"),
        ("vehicle_id", "string"), ("stops", "int"), ("km", "double"), ("duration_min", "double"), ("cost_thb", "double")])

# COMMAND ----------

@dp.table(name="gold_cash_nodes", comment="Gold servable cash nodes: branches, ATMs, and RCMs.",
          table_properties=GOLD_PROPERTIES)
def gold_cash_nodes():
    branches = spark.read.table("silver_branches").select(
        F.col("branch_id").alias("node_id"), F.lit("BRANCH").alias("node_type"),
        F.col("branch_name").alias("node_name"), "district", "depot_id", "lat", "lng",
        F.col("vault_capacity_thb").alias("capacity_thb"), "min_cash_thb", "open_min", "close_min")
    machines = spark.read.table("silver_machines").select(
        F.col("machine_id").alias("node_id"), F.col("machine_type").alias("node_type"), F.col("site_name").alias("node_name"),
        "district", "depot_id", "lat", "lng", F.col("cassette_capacity_thb").alias("capacity_thb"),
        "min_cash_thb", F.lit(480).cast("int").alias("open_min"), F.lit(1320).cast("int").alias("close_min"))
    return branches.unionByName(machines)

@dp.table(name="gold_node_daily", comment="Gold unified daily cash flows per cash node.",
          table_properties=GOLD_PROPERTIES)
def gold_node_daily():
    machines = spark.read.table("silver_machine_daily").join(spark.read.table("silver_machines").select("machine_id", "machine_type", "depot_id"), "machine_id").select(
        F.col("machine_id").alias("node_id"), "machine_type", "depot_id", "txn_date",
        (F.col("withdrawals_thb") - F.col("deposits_thb")).alias("net_outflow_thb"), "closing_cash_thb", "cash_out_flag")
    branches = spark.read.table("silver_branch_daily").join(spark.read.table("silver_branches").select("branch_id", "depot_id"), "branch_id").select(
        F.col("branch_id").alias("node_id"), F.lit("BRANCH").alias("node_type"), "depot_id", "txn_date",
        (F.col("outflow_thb") - F.col("inflow_thb")).alias("net_outflow_thb"),
        F.col("closing_vault_thb").alias("closing_cash_thb"), F.lit(False).alias("cash_out_flag"))
    return machines.withColumnRenamed("machine_type", "node_type").unionByName(branches)

@dp.table(name="gold_demand_features", comment="Gold training and scoring features with lag and rolling cash-demand features.",
          table_properties=GOLD_PROPERTIES)
def gold_demand_features():
    daily = spark.read.table("gold_node_daily")
    cal = spark.read.table("silver_calendar").select(F.col("cal_date").alias("txn_date"), "dow", "is_weekend", "is_holiday", "is_payday")
    w = Window.partitionBy("node_id").orderBy("txn_date")
    w7 = w.rowsBetween(-7, -1)
    w28 = w.rowsBetween(-28, -1)
    return (daily.join(cal, "txn_date")
        .withColumn("dom", F.dayofmonth("txn_date"))
        .withColumn("lag_1", F.lag("net_outflow_thb", 1).over(w))
        .withColumn("lag_7", F.lag("net_outflow_thb", 7).over(w))
        .withColumn("lag_14", F.lag("net_outflow_thb", 14).over(w))
        .withColumn("roll7_mean", F.avg("net_outflow_thb").over(w7))
        .withColumn("roll28_mean", F.avg("net_outflow_thb").over(w28))
        .select("node_id", "node_type", "txn_date", "dow", "dom", "is_weekend", "is_holiday", "is_payday",
                "lag_1", "lag_7", "lag_14", "roll7_mean", "roll28_mean", "net_outflow_thb"))

@dp.table(name="gold_node_status", comment="Gold latest cash-node status snapshot as of 2026-09-30.",
          table_properties=GOLD_PROPERTIES)
def gold_node_status():
    snapshot = spark.read.table("gold_node_daily").where("txn_date = DATE'2026-09-30'")
    recent = spark.read.table("gold_node_daily").where("txn_date BETWEEN DATE'2026-09-03' AND DATE'2026-09-30'")
    averages = recent.groupBy("node_id").agg(F.avg("net_outflow_thb").alias("avg_daily_outflow_28d"))
    return (spark.read.table("gold_cash_nodes").join(snapshot.select("node_id", "closing_cash_thb"), "node_id")
        .join(averages, "node_id")
        .select("node_id", "node_type", "node_name", "district", "depot_id", "lat", "lng", "capacity_thb",
                "min_cash_thb", F.col("closing_cash_thb").alias("current_cash_thb"),
                F.greatest(F.lit(0.0), F.col("avg_daily_outflow_28d")).alias("avg_daily_outflow_28d"),
                F.lit("2026-09-30").cast("date").alias("as_of_date")))

@dp.table(name="gold_baseline_daily", comment="Gold daily KPIs for the historical fixed-cycle CIT baseline plan.",
          table_properties=GOLD_PROPERTIES)
def gold_baseline_daily():
    return (spark.read.table("silver_cit_trips").groupBy("service_date", "depot_id").agg(
        F.countDistinct("vehicle_id").cast("int").alias("vehicles_used"), F.sum("stops").cast("int").alias("stops"),
        F.sum("km").alias("km"), F.sum("duration_min").alias("duration_min"), F.sum("cost_thb").alias("cost_thb")))
