# Databricks notebook source
# MAGIC %md
# MAGIC # Deploy Genie Agent: SNB Cash Ops Assistant
# MAGIC Idempotent create/update by title. Prints `space_id` for the e2e job and the app.
# MAGIC Gold pipeline tables are required. ML route tables are attached when they exist.

# COMMAND ----------

# MAGIC %pip install pyyaml databricks-sdk --quiet

# COMMAND ----------

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import yaml
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.workspace import ImportFormat

try:
    dbutils.widgets.text("catalog", "stable_classic_nan_fe_vm_catalog")
    dbutils.widgets.text("schema", "snb_cash_ops")
    CATALOG = dbutils.widgets.get("catalog")
    SCHEMA = dbutils.widgets.get("schema")
    IN_NOTEBOOK = True
except NameError:
    CATALOG = "stable_classic_nan_fe_vm_catalog"
    SCHEMA = "snb_cash_ops"
    IN_NOTEBOOK = False

TITLE = "SNB Cash Ops Assistant"
EMBEDDED_SPACE_YAML = '# SNB Cash Ops Assistant — Genie Agent (formerly Genie space).\n# Deployed by 01_deploy_genie.py (idempotent: find-or-create by title).\n# {S} is replaced with catalog.schema. IDs are content hashes so redeploys stay stable.\ntitle: "SNB Cash Ops Assistant"\ndescription: >-\n  Cash operations assistant for Siam Northeast Bank (SNB) in Khon Kaen: node cash-out\n  risk, idle cash by depot, CIT cost and van usage. Reads gold tables in\n  stable_classic_nan_fe_vm_catalog.snb_cash_ops. Synthetic demo data.\nwarehouse_id: "23189fee7d892fb8"\nschema: stable_classic_nan_fe_vm_catalog.snb_cash_ops\n\ntables:\n  gold_cash_nodes: "One row per servable node (BRANCH, ATM, RCM): identity, depot, capacity, hours."\n  gold_node_daily: "Daily unified cash flow per node. net_outflow_thb is cash leaving the node. History 2025-04-01 to 2026-09-30."\n  gold_demand_features: "Training/scoring features (lags, rolling means, calendar flags) plus label net_outflow_thb."\n  gold_node_status: "Latest snapshot per node. as_of_date is 2026-09-30. current_cash_thb and avg_daily_outflow_28d drive days-to-cash-out."\n  gold_baseline_daily: "Historical fixed-cycle CIT plan KPIs per depot and service_date (vehicles_used, stops, km, cost_thb)."\n  gold_demand_forecast: "ML 7-day net-outflow forecast from 2026-10-01 (horizon_day 1..7). Optional until ML job lands."\n  gold_replenishment_orders: "Nodes needing a visit on service_date with action DELIVER|PICKUP, days_to_cashout, priority CRITICAL|HIGH|NORMAL."\n  gold_routes: "CIT routes for OPTIMIZED vs BASELINE plan_type on service_date (usually 2026-10-01)."\n  gold_route_stops: "Ordered stops on each route with ETA, action, amount_thb."\n  gold_route_summary: "Day-level KPIs by plan_type: cost_thb, vehicles_used, idle_cash_thb, cashout_risk_nodes, sla_pct."\n  gold_model_metrics: "Forecast quality (MAPE/WAPE) by model_version and segment (node_type)."\n\nvalue_columns:\n  gold_cash_nodes: [node_type, district, depot_id]\n  gold_node_status: [node_type, district, depot_id]\n  gold_replenishment_orders: [node_type, depot_id, action, priority]\n  gold_routes: [plan_type, depot_id]\n  gold_route_summary: [plan_type]\n\nsample_questions:\n  - "Which nodes run out of cash in the next 3 days if we do nothing?"\n  - "What is CIT cost of optimized vs baseline for 2026-10-01?"\n  - "How much idle cash is sitting in each depot as of 2026-09-30?"\n  - "How many vans were used on the last baseline day versus the optimized plan?"\n  - "Which districts have the highest cash-out risk?"\n  - "Show forecast WAPE by node type"\n\ninstructions: |\n  You are the SNB Cash Ops Assistant for Siam Northeast Bank (fictional), Khon Kaen province.\n  Audience: cash-ops dispatchers, CIT planners, and the CFO. Answer in concise business English.\n  Currency is Thai baht (THB). Never use a real bank name. Never invent nodes, costs, or van counts.\n\n  ## Grain and dates\n  - Node snapshot as_of_date = 2026-09-30 (gold_node_status).\n  - History window = 2025-04-01 to 2026-09-30 (gold_node_daily, gold_baseline_daily).\n  - Optimized CIT plan_date / service_date = 2026-10-01 when ML route tables exist.\n  - Always state the date and grain in the answer (per node, per depot, per plan_type, per day).\n\n  ## Which table to use\n  - Cash-out / run-out / days of cash left: prefer gold_replenishment_orders.days_to_cashout and priority\n    when that table exists. If it does not exist, approximate from gold_node_status:\n    days_to_cashout = current_cash_thb / NULLIF(avg_daily_outflow_28d, 0)\n    and treat avg_daily_outflow_28d <= 0 as "not draining" (exclude from cash-out lists).\n  - Node master / names / coords: gold_cash_nodes. Join to facts on node_id.\n  - Daily history / payday spikes: gold_node_daily (join gold_demand_features on node_id, txn_date for calendar flags).\n  - Idle cash by depot: SUM(current_cash_thb) on gold_node_status grouped by depot_id (join gold_cash_nodes for names).\n  - Historical CIT cost and vans: gold_baseline_daily (fixed-cycle plan). Last history day is 2026-09-30.\n  - Optimized vs baseline CIT for 2026-10-01: gold_route_summary (plan_type OPTIMIZED vs BASELINE).\n    If gold_route_summary is missing, say the ML route job has not landed yet and fall back to gold_baseline_daily\n    for the historical cycle only — do not invent an optimized cost.\n  - Van / vehicle counts for the optimized day: gold_route_summary.vehicles_used or COUNT(DISTINCT vehicle_id) on gold_routes.\n  - Forecast quality: gold_model_metrics. metric values are WAPE_model, WAPE_naive, MAPE_model, MAPE_naive,\n    P80_coverage; segment is ATM | BRANCH | RCM | ALL. "WAPE" means WAPE_model; compare against WAPE_naive (lag-7 naive).\n  - Do not query bronze or silver tables. Gold only.\n\n  ## Agent mode / skills\n  Use Agent mode for multi-step ops questions. Match the question to one skill and follow its output shape:\n  - cash-out-risk: nodes that cash out within N days (default 3).\n  - cit-cost-compare: OPTIMIZED vs BASELINE cost, km, vans, SLA, idle cash.\n  - idle-cash-by-depot: current_cash_thb rolled to depot.\n  - vans-used: vehicles_used for a date and plan.\n  One trusted SQL per skill when Chat mode is used; Agent mode may run the skill SQL then a short narrative.\n\n  ## Style\n  Summarize the number first, then a short table. Round THB to the nearest thousand for exec answers unless asked for exact.\n  Cite filters (service_date, plan_type, depot_id). If a gold ML table is absent, say so in one sentence and use the pipeline fallback.\n\njoins:\n  - left: {identifier: "{S}.gold_node_daily", alias: gold_node_daily}\n    right: {identifier: "{S}.gold_cash_nodes", alias: gold_cash_nodes}\n    sql: "`gold_node_daily`.`node_id` = `gold_cash_nodes`.`node_id`"\n    rel: FROM_RELATIONSHIP_TYPE_MANY_TO_ONE\n  - left: {identifier: "{S}.gold_node_status", alias: gold_node_status}\n    right: {identifier: "{S}.gold_cash_nodes", alias: gold_cash_nodes}\n    sql: "`gold_node_status`.`node_id` = `gold_cash_nodes`.`node_id`"\n    rel: FROM_RELATIONSHIP_TYPE_ONE_TO_ONE\n  - left: {identifier: "{S}.gold_demand_features", alias: gold_demand_features}\n    right: {identifier: "{S}.gold_cash_nodes", alias: gold_cash_nodes}\n    sql: "`gold_demand_features`.`node_id` = `gold_cash_nodes`.`node_id`"\n    rel: FROM_RELATIONSHIP_TYPE_MANY_TO_ONE\n  - left: {identifier: "{S}.gold_demand_forecast", alias: gold_demand_forecast}\n    right: {identifier: "{S}.gold_cash_nodes", alias: gold_cash_nodes}\n    sql: "`gold_demand_forecast`.`node_id` = `gold_cash_nodes`.`node_id`"\n    rel: FROM_RELATIONSHIP_TYPE_MANY_TO_ONE\n  - left: {identifier: "{S}.gold_replenishment_orders", alias: gold_replenishment_orders}\n    right: {identifier: "{S}.gold_cash_nodes", alias: gold_cash_nodes}\n    sql: "`gold_replenishment_orders`.`node_id` = `gold_cash_nodes`.`node_id`"\n    rel: FROM_RELATIONSHIP_TYPE_MANY_TO_ONE\n  - left: {identifier: "{S}.gold_route_stops", alias: gold_route_stops}\n    right: {identifier: "{S}.gold_routes", alias: gold_routes}\n    sql: "`gold_route_stops`.`service_date` = `gold_routes`.`service_date` AND `gold_route_stops`.`plan_type` = `gold_routes`.`plan_type` AND `gold_route_stops`.`route_id` = `gold_routes`.`route_id`"\n    rel: FROM_RELATIONSHIP_TYPE_MANY_TO_ONE\n  - left: {identifier: "{S}.gold_routes", alias: gold_routes}\n    right: {identifier: "{S}.gold_route_summary", alias: gold_route_summary}\n    sql: "`gold_routes`.`service_date` = `gold_route_summary`.`service_date` AND `gold_routes`.`plan_type` = `gold_route_summary`.`plan_type`"\n    rel: FROM_RELATIONSHIP_TYPE_MANY_TO_ONE\n\nexamples:\n  - question: "Which nodes run out of cash in the next 3 days if we do nothing?"\n    usage: "Cash-out risk. Prefer replenishment_orders; fallback divides current cash by 28-day average outflow."\n    sql: |\n      SELECT\n        s.node_id,\n        n.node_type,\n        n.node_name,\n        s.depot_id,\n        s.current_cash_thb,\n        s.avg_daily_outflow_28d,\n        s.current_cash_thb / NULLIF(s.avg_daily_outflow_28d, 0) AS days_to_cashout\n      FROM {S}.gold_node_status s\n      JOIN {S}.gold_cash_nodes n ON s.node_id = n.node_id\n      WHERE s.avg_daily_outflow_28d > 0\n        AND s.current_cash_thb / s.avg_daily_outflow_28d <= 3\n      ORDER BY days_to_cashout ASC\n      LIMIT 25\n  - question: "Which nodes cash out in 3 days using replenishment orders?"\n    usage: "Use when gold_replenishment_orders exists. Plan date 2026-10-01."\n    sql: |\n      SELECT node_id, node_type, node_name, depot_id, days_to_cashout, priority, action, amount_thb\n      FROM {S}.gold_replenishment_orders\n      WHERE service_date = DATE \'2026-10-01\'\n        AND days_to_cashout <= 3\n      ORDER BY days_to_cashout ASC, priority\n  - question: "What is CIT cost of optimized vs baseline for 2026-10-01?"\n    usage: "Day-level plan comparison. Requires gold_route_summary."\n    sql: |\n      SELECT plan_type, routes, vehicles_used, stops, km, duration_hr, cost_thb,\n             idle_cash_thb, cashout_risk_nodes, sla_pct\n      FROM {S}.gold_route_summary\n      WHERE service_date = DATE \'2026-10-01\'\n      ORDER BY plan_type\n  - question: "How much idle cash is sitting in each depot as of 2026-09-30?"\n    usage: "Idle cassette/vault cash from the snapshot, not in-transit CIT."\n    sql: |\n      SELECT\n        s.depot_id,\n        COUNT(*) AS nodes,\n        SUM(s.current_cash_thb) AS idle_cash_thb\n      FROM {S}.gold_node_status s\n      WHERE s.as_of_date = DATE \'2026-09-30\'\n      GROUP BY s.depot_id\n      ORDER BY s.depot_id\n  - question: "How many vans were used on the last baseline day versus the optimized plan?"\n    usage: "Baseline vans from gold_baseline_daily on 2026-09-30; optimized vans from gold_route_summary on 2026-10-01."\n    sql: |\n      SELECT \'BASELINE\' AS plan_type, DATE \'2026-09-30\' AS service_date,\n             SUM(vehicles_used) AS vehicles_used, SUM(cost_thb) AS cost_thb\n      FROM {S}.gold_baseline_daily\n      WHERE service_date = DATE \'2026-09-30\'\n      UNION ALL\n      SELECT plan_type, service_date, vehicles_used, cost_thb\n      FROM {S}.gold_route_summary\n      WHERE service_date = DATE \'2026-10-01\' AND plan_type = \'OPTIMIZED\'\n  - question: "Which districts have the highest cash-out risk?"\n    usage: "District rollup of nodes with <= 3 days of cash."\n    sql: |\n      SELECT\n        n.district,\n        COUNT(*) AS at_risk_nodes,\n        SUM(s.current_cash_thb) AS cash_thb\n      FROM {S}.gold_node_status s\n      JOIN {S}.gold_cash_nodes n ON s.node_id = n.node_id\n      WHERE s.avg_daily_outflow_28d > 0\n        AND s.current_cash_thb / s.avg_daily_outflow_28d <= 3\n      GROUP BY n.district\n      ORDER BY at_risk_nodes DESC\n\n  - question: "Show forecast WAPE by node type"\n    usage: "Model vs lag-7 naive WAPE per segment from gold_model_metrics."\n    sql: |\n      SELECT\n        segment AS node_type,\n        MAX(CASE WHEN metric = \'WAPE_model\' THEN value END) AS wape_model,\n        MAX(CASE WHEN metric = \'WAPE_naive\' THEN value END) AS wape_naive\n      FROM {S}.gold_model_metrics\n      WHERE metric IN (\'WAPE_model\', \'WAPE_naive\')\n      GROUP BY segment\n      ORDER BY segment\n\nsql_snippets:\n  measures:\n    - name: Idle cash THB\n      sql: "SUM(`{S}`.`gold_node_status`.`current_cash_thb`) AS idle_cash_thb"\n      synonyms: [idle cash, cassette cash, vault cash]\n    - name: CIT cost THB\n      sql: "SUM(`{S}`.`gold_baseline_daily`.`cost_thb`) AS cit_cost_thb"\n      synonyms: [cit cost, trip cost]\n  expressions:\n    - name: Days to cash-out\n      sql: "`{S}`.`gold_node_status`.`current_cash_thb` / NULLIF(`{S}`.`gold_node_status`.`avg_daily_outflow_28d`, 0) AS days_to_cashout"\n      synonyms: [days of cash, run-out days, cash-out horizon]\n  filters:\n    - name: Cash-out within 3 days\n      sql: "`{S}`.`gold_node_status`.`avg_daily_outflow_28d` > 0 AND `{S}`.`gold_node_status`.`current_cash_thb` / `{S}`.`gold_node_status`.`avg_daily_outflow_28d` <= 3"\n      synonyms: [cash out in 3 days, run out soon]\n    - name: Plan date 1 Oct 2026\n      sql: "`service_date` = DATE \'2026-10-01\'"\n      synonyms: [plan date, tomorrow plan, "2026-10-01"]\n\nbenchmarks:\n  - q: ["Which nodes run out of cash in the next 3 days if we do nothing?"]\n    sql: |\n      SELECT s.node_id, n.node_name, s.depot_id,\n             s.current_cash_thb / NULLIF(s.avg_daily_outflow_28d, 0) AS days_to_cashout\n      FROM {S}.gold_node_status s\n      JOIN {S}.gold_cash_nodes n ON s.node_id = n.node_id\n      WHERE s.avg_daily_outflow_28d > 0\n        AND s.current_cash_thb / s.avg_daily_outflow_28d <= 3\n      ORDER BY days_to_cashout\n  - q: ["How much idle cash is sitting in each depot as of 2026-09-30?"]\n    sql: |\n      SELECT depot_id, SUM(current_cash_thb) AS idle_cash_thb\n      FROM {S}.gold_node_status\n      WHERE as_of_date = DATE \'2026-09-30\'\n      GROUP BY depot_id\n  - q: ["How many vans did the fixed-cycle plan use on 2026-09-30?"]\n    sql: |\n      SELECT SUM(vehicles_used) AS vehicles_used, SUM(cost_thb) AS cost_thb\n      FROM {S}.gold_baseline_daily\n      WHERE service_date = DATE \'2026-09-30\'\n'

WAREHOUSE_ID = "23189fee7d892fb8"
FQ = f"{CATALOG}.{SCHEMA}"
PIPELINE_GOLD = [
    "gold_cash_nodes",
    "gold_node_daily",
    "gold_demand_features",
    "gold_node_status",
    "gold_baseline_daily",
]
ML_GOLD = [
    "gold_demand_forecast",
    "gold_replenishment_orders",
    "gold_routes",
    "gold_route_stops",
    "gold_route_summary",
    "gold_model_metrics",
]
OWNER_EMAIL = "nan.chulpaibul@databricks.com"
SKILL_WS_ROOT = f"/Workspace/Users/{OWNER_EMAIL}/.assistant/skills"

w = WorkspaceClient() if IN_NOTEBOOK else WorkspaceClient(profile="nan-demo")


def hid(*parts: str) -> str:
    return hashlib.md5("|".join(parts).encode()).hexdigest()


def sql_lines(sql: str) -> list[str]:
    sql = sql.strip().replace("{S}", FQ)
    lines = sql.splitlines()
    return [line + "\n" for line in lines[:-1]] + [lines[-1]]


def _here() -> Path:
    try:
        return Path(__file__).resolve().parent
    except NameError:
        return Path.cwd()


def load_cfg() -> dict:
    candidates = [
        _here() / "space.yaml",
        Path.cwd() / "space.yaml",
        Path.cwd() / "genie" / "space.yaml",
    ]
    try:
        nb = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
        folder = nb.rsplit("/", 1)[0]
        if not folder.startswith("/Workspace"):
            folder = "/Workspace" + folder
        candidates.append(Path(folder) / "space.yaml")
    except Exception:
        pass
    for path in candidates:
        try:
            if path.exists():
                print("Loaded space.yaml from", path)
                return yaml.safe_load(path.read_text())
        except Exception as exc:
            print("skip", path, exc)
    print("space.yaml missing on disk; using embedded copy")
    return yaml.safe_load(EMBEDDED_SPACE_YAML)


def list_tables() -> set[str]:
    stmt = w.api_client.do(
        "POST",
        "/api/2.0/sql/statements",
        body={
            "statement": f"SHOW TABLES IN {FQ}",
            "warehouse_id": WAREHOUSE_ID,
            "wait_timeout": "50s",
            "format": "JSON_ARRAY",
        },
    )
    rows = (stmt.get("result") or {}).get("data_array") or []
    # SHOW TABLES columns: database, tableName, isTemporary
    names = {r[1] for r in rows if len(r) > 1}
    print("listed", len(names), "tables", flush=True)
    return names


def wait_for_ml(timeout_sec: int = 45, interval: int = 15) -> set[str]:
    """Brief poll so an e2e run can attach route tables written moments earlier."""
    deadline = time.time() + timeout_sec
    names: set[str] = set()
    while True:
        try:
            names = list_tables()
        except Exception as exc:
            print("list_tables retry:", str(exc)[:300], flush=True)
        if set(PIPELINE_GOLD).issubset(names) and (
            set(ML_GOLD).issubset(names) or time.time() >= deadline
        ):
            return names
        if time.time() >= deadline:
            return names
        missing = [t for t in ML_GOLD if t not in names]
        print("waiting for ML gold:", missing, flush=True)
        time.sleep(interval)


def table_entry(name: str, desc: str, value_columns: dict) -> dict:
    entry = {"identifier": f"{FQ}.{name}", "description": [desc]}
    cols = value_columns.get(name)
    if cols:
        entry["column_configs"] = [
            {
                "column_name": c,
                "enable_format_assistance": True,
                "enable_entity_matching": True,
            }
            for c in sorted(cols)
        ]
    return entry


def build_space(cfg: dict, present: set[str]) -> dict:
    wanted = [t for t in PIPELINE_GOLD + ML_GOLD if t in present and t in cfg["tables"]]
    if not set(PIPELINE_GOLD).issubset(present):
        missing = [t for t in PIPELINE_GOLD if t not in present]
        raise RuntimeError(f"required pipeline gold tables missing: {missing}")

    joins = []
    for spec in cfg.get("joins", []):
        left_id = spec["left"]["identifier"].replace("{S}", FQ)
        right_id = spec["right"]["identifier"].replace("{S}", FQ)
        left_tbl = left_id.rsplit(".", 1)[-1]
        right_tbl = right_id.rsplit(".", 1)[-1]
        if left_tbl not in present or right_tbl not in present:
            continue
        joins.append(
            {
                "id": hid("join", left_id, right_id),
                "left": {
                    "identifier": left_id,
                    "alias": spec["left"]["alias"],
                },
                "right": {
                    "identifier": right_id,
                    "alias": spec["right"]["alias"],
                },
                "sql": [
                    spec["sql"].replace("{S}", FQ),
                    f"--rt={spec['rel']}--",
                ],
            }
        )

    examples = []
    for ex in cfg.get("examples", []):
        sql = ex["sql"]
        # Skip ML-only examples when those tables are absent.
        if "gold_replenishment_orders" in sql and "gold_replenishment_orders" not in present:
            continue
        if "gold_route_summary" in sql and "gold_route_summary" not in present:
            continue
        examples.append(
            {
                "id": hid("example", ex["question"]),
                "question": [ex["question"]],
                "sql": sql_lines(sql),
                "usage_guidance": [ex.get("usage", "")],
            }
        )

    snippets = {}
    for kind, items in cfg.get("sql_snippets", {}).items():
        snippets[kind] = sorted(
            [
                {
                    "id": hid("snippet", kind, s["name"]),
                    "sql": [s["sql"].replace("{S}", FQ)],
                    "display_name": s["name"],
                    "synonyms": [str(x) for x in s.get("synonyms", [])],
                }
                for s in items
            ],
            key=lambda x: x["id"],
        )

    ml_note = ""
    missing_ml = [t for t in ML_GOLD if t not in present]
    if missing_ml:
        ml_note = (
            "\n\n## Current table coverage\n"
            "ML gold tables not yet in the space: "
            + ", ".join(missing_ml)
            + ". Route / optimized-vs-baseline questions will work after the ML job writes them; "
            "re-run this notebook to attach them."
        )

    space = {
        "version": 2,
        "config": {
            "sample_questions": sorted(
                [{"id": hid("sample", q), "question": [q]} for q in cfg["sample_questions"]],
                key=lambda x: x["id"],
            )
        },
        "data_sources": {
            "tables": sorted(
                [table_entry(n, cfg["tables"][n], cfg.get("value_columns", {})) for n in wanted],
                key=lambda x: x["identifier"],
            )
        },
        "instructions": {
            "text_instructions": [
                {"id": hid("instructions"), "content": [cfg["instructions"] + ml_note]}
            ],
            "example_question_sqls": sorted(examples, key=lambda x: x["id"]),
            "join_specs": sorted(joins, key=lambda x: x["id"]),
            "sql_snippets": snippets,
        },
        "benchmarks": {
            "questions": sorted(
                [
                    {
                        "id": hid("bench", q),
                        "question": [q],
                        "answer": [{"format": "SQL", "content": sql_lines(b["sql"])}],
                    }
                    for b in cfg["benchmarks"]
                    for q in b["q"]
                ],
                key=lambda x: x["id"],
            )
        },
    }
    return space, wanted, missing_ml


def find_space_id() -> str | None:
    token = None
    seen = set()
    for _ in range(20):
        page = w.genie.list_spaces(page_token=token) if token else w.genie.list_spaces()
        for s in page.spaces or []:
            if s.title == TITLE:
                return s.space_id
        token = page.next_page_token
        if not token or token in seen:
            return None
        seen.add(token)
    return None


def upload_skills() -> None:
    skills_dir = _here() / "skills"
    if not skills_dir.exists():
        skills_dir = Path.cwd() / "genie" / "skills"
    if not skills_dir.exists():
        print("no local skills dir, skip upload")
        return
    for skill_md in skills_dir.glob("*/SKILL.md"):
        dest = f"{SKILL_WS_ROOT}/{skill_md.parent.name}/SKILL.md"
        w.workspace.mkdirs(f"{SKILL_WS_ROOT}/{skill_md.parent.name}")
        w.workspace.upload(
            dest,
            skill_md.read_bytes(),
            format=ImportFormat.RAW,
            overwrite=True,
        )
        print("uploaded skill", dest)


# COMMAND ----------

cfg = load_cfg()
cfg["schema"] = FQ
present = wait_for_ml()
print("tables present:", sorted(present))
space, wanted, missing_ml = build_space(cfg, present)
serialized = json.dumps(space, ensure_ascii=False, default=str)
body = {
    "title": TITLE,
    "description": cfg["description"],
    "warehouse_id": WAREHOUSE_ID,
    "serialized_space": serialized,
}

space_id = find_space_id()
if space_id:
    w.api_client.do("PATCH", f"/api/2.0/genie/spaces/{space_id}", body=body)
    action = "updated"
else:
    resp = w.api_client.do("POST", "/api/2.0/genie/spaces", body=body)
    space_id = resp["space_id"]
    action = "created"

upload_skills()
host = w.config.host.rstrip("/")
url = f"{host}/genie/rooms/{space_id}"
print(action, "space")
print("SPACE_ID=" + space_id)
print("URL=" + url)
print("TABLES=" + ",".join(wanted))
print("MISSING_ML=" + ",".join(missing_ml) if missing_ml else "MISSING_ML=")
print(space_id)
