"""App settings: config.yaml defaults overridden by environment (app.yaml in Databricks Apps)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.yaml"


def _truthy(v: str | bool | None, default: bool = False) -> bool:
    if v is None or v == "":
        return default
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class AppSettings:
    catalog: str
    schema: str
    warehouse_id: str
    serving_endpoint: str
    genie_space_id: str
    plan_date: str
    force_mock: bool
    lakebase_endpoint: str  # projects/<p>/branches/<b>/endpoints/<e> (Autoscaling)
    pg_host: str
    pg_database: str
    pg_user: str
    pg_port: int
    pg_sslmode: str

    @property
    def fq(self) -> str:
        return f"{self.catalog}.{self.schema}"

    def table(self, name: str) -> str:
        return f"{self.fq}.{name}"


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    raw: dict = {}
    if CONFIG_PATH.is_file():
        with CONFIG_PATH.open() as f:
            raw = yaml.safe_load(f) or {}

    def pick(env: str, key: str, default: str = "") -> str:
        return os.getenv(env) or str(raw.get(key) or default)

    return AppSettings(
        catalog=pick("CATALOG", "catalog", "stable_classic_nan_fe_vm_catalog"),
        schema=pick("SCHEMA", "schema", "snb_cash_ops"),
        warehouse_id=os.getenv("WAREHOUSE_ID")
        or os.getenv("DATABRICKS_WAREHOUSE_ID")
        or str(raw.get("warehouse_id") or ""),
        serving_endpoint=pick("SERVING_ENDPOINT", "serving_endpoint", "snb-cash-forecast"),
        genie_space_id=pick("GENIE_SPACE_ID", "genie_space_id", ""),
        plan_date=pick("PLAN_DATE", "plan_date", "2026-10-01"),
        force_mock=_truthy(os.getenv("USE_MOCK"), _truthy(raw.get("use_mock"), False)),
        lakebase_endpoint=pick("LAKEBASE_ENDPOINT", "lakebase_endpoint", ""),
        pg_host=os.getenv("PGHOST", ""),
        pg_database=os.getenv("PGDATABASE", "databricks_postgres"),
        pg_user=os.getenv("PGUSER", "") or os.getenv("DATABRICKS_CLIENT_ID", ""),
        pg_port=int(os.getenv("PGPORT", "5432") or 5432),
        pg_sslmode=os.getenv("PGSSLMODE", "require"),
    )
