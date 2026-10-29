# Databricks notebook source
# UC governance controls for the synthetic SNB cash logistics demo.
dbutils.widgets.text("catalog", "stable_classic_nan_fe_vm_catalog")
dbutils.widgets.text("schema", "snb_cash_ops")
catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")
fq_schema = f"`{catalog}`.`{schema}`"
owner = "nan.chulpaibul@databricks.com"

def run(sql, optional=False):
    try:
        print("SQL>", sql.replace("\n", " "))
        return spark.sql(sql)
    except Exception as exc:
        if optional:
            print("OPTIONAL CONTROL NOT APPLIED:", str(exc)[:500])
            return None
        raise

# COMMAND ----------

# Functions are independently managed UC objects. They are created before policy attachment.
run(f"""
CREATE OR REPLACE FUNCTION {fq_schema}.snb_mask_custodian(name STRING)
RETURNS STRING
RETURN CASE
  WHEN is_account_group_member('snb_pii_readers')
       OR is_account_group_member('admins')
       OR current_user() = '{owner}' THEN name
  ELSE '***'
END
""")

run(f"""
CREATE OR REPLACE FUNCTION {fq_schema}.snb_depot_filter(depot_id STRING)
RETURNS BOOLEAN
RETURN CASE
  WHEN is_member('admins') THEN TRUE
  WHEN is_member('snb_ops_kkn_c') THEN depot_id = 'DEP-KKN-C'
  ELSE FALSE
END
""")

# COMMAND ----------

layers = {
    "bronze": ["bronze_depots", "bronze_vehicles", "bronze_branches", "bronze_machines",
               "bronze_calendar", "bronze_machine_daily", "bronze_branch_daily", "bronze_cit_trips"],
    "silver": ["silver_depots", "silver_vehicles", "silver_branches", "silver_machines",
               "silver_calendar", "silver_machine_daily", "silver_branch_daily", "silver_cit_trips"],
    "gold": ["gold_cash_nodes", "gold_node_daily", "gold_demand_features", "gold_node_status", "gold_baseline_daily"],
}
for layer, tables in layers.items():
    for table in tables:
        # Apply separately: centrally governed tag policies can reject one key without
        # preventing the portable layer classification from being retained.
        run(f"ALTER TABLE {fq_schema}.`{table}` SET TAGS ('layer' = '{layer}')", optional=True)
        run(f"ALTER TABLE {fq_schema}.`{table}` SET TAGS ('data_domain' = 'cash_logistics')", optional=True)
        run(f"COMMENT ON TABLE {fq_schema}.`{table}` IS 'Synthetic SNB cash-logistics {layer} layer dataset.'", optional=True)
        # SDP owns the physical table definition, so column descriptions are
        # applied post-publication and kept idempotent here.
        try:
            for field in spark.catalog.listColumns(f"{catalog}.{schema}.{table}"):
                run(
                    f"COMMENT ON COLUMN {fq_schema}.`{table}`.`{field.name}` "
                    f"IS 'Synthetic SNB cash-logistics {layer} field: {field.name}.'",
                    optional=True,
                )
        except Exception as exc:
            print("COLUMN COMMENT ENUMERATION SKIPPED:", table, str(exc)[:300])

for column in ["custodian_name", "custodian_phone"]:
    run(f"ALTER TABLE {fq_schema}.silver_vehicles ALTER COLUMN {column} SET TAGS "
        "('pii' = 'address')", optional=True)
    run(f"ALTER TABLE {fq_schema}.silver_vehicles ALTER COLUMN {column} SET TAGS "
        "('data_domain' = 'cash_logistics')", optional=True)
    run(f"ALTER TABLE {fq_schema}.silver_vehicles ALTER COLUMN {column} SET TAGS "
        "('sensitivity' = 'confidential')", optional=True)
    run(f"COMMENT ON COLUMN {fq_schema}.silver_vehicles.{column} IS "
        "'Synthetic custodian PII protected by snb_mask_custodian.'", optional=True)
    run(f"ALTER TABLE {fq_schema}.silver_vehicles ALTER COLUMN {column} SET MASK {fq_schema}.snb_mask_custodian", optional=True)

# Pipeline-managed tables can reject direct row-filter changes. Use an audited governed view if so.
row_filter_sql = f"ALTER TABLE {fq_schema}.silver_cit_trips SET ROW FILTER {fq_schema}.snb_depot_filter ON (depot_id)"
if run(row_filter_sql, optional=True) is None:
    run(f"""
    CREATE OR REPLACE VIEW {fq_schema}.silver_cit_trips_governed AS
    SELECT * FROM {fq_schema}.silver_cit_trips
    WHERE {fq_schema}.snb_depot_filter(depot_id)
    """)
    print("Row filter fallback: silver_cit_trips_governed applies snb_depot_filter.")

# COMMAND ----------

run(f"GRANT USE SCHEMA ON SCHEMA {fq_schema} TO `account users`", optional=True)
for table in layers["gold"]:
    run(f"GRANT SELECT ON TABLE {fq_schema}.`{table}` TO `account users`", optional=True)
run(f"GRANT READ VOLUME ON VOLUME `{catalog}`.`{schema}`.`raw` TO `{owner}`", optional=True)

print("\nGovernance summary")
tag_rows = run(f"""
SELECT table_name, column_name, tag_name, tag_value
FROM {catalog}.information_schema.column_tags
WHERE table_schema = '{schema}' AND table_name = 'silver_vehicles'
ORDER BY column_name, tag_name
""", optional=True)
if tag_rows is not None:
    tag_rows.show(truncate=False)

for function_name in ["snb_mask_custodian", "snb_depot_filter"]:
    run(f"DESCRIBE FUNCTION EXTENDED {fq_schema}.{function_name}", optional=True).show(truncate=False)

masked = run(f"SELECT vehicle_id, custodian_name, custodian_phone FROM {fq_schema}.silver_vehicles ORDER BY vehicle_id LIMIT 3", optional=True)
if masked is not None:
    masked.show(truncate=False)
print("Governance controls applied.")
