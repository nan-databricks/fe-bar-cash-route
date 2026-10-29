"""Lakebase Postgres (Autoscaling project `snb-cash-ops`) access for public.dispatch_overrides.

Connection params come from the Databricks Apps postgres/database resource env vars
(PGHOST, PGDATABASE, PGUSER, PGPORT, PGSSLMODE). The password is a short-lived OAuth token:
  * LAKEBASE_ENDPOINT set -> w.postgres.generate_database_credential(endpoint=...).token
  * otherwise             -> the workspace OAuth token of the app service principal / user.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any

from server.settings import get_settings

log = logging.getLogger(__name__)

_TOKEN: dict[str, Any] = {"value": None, "exp": 0.0}
_LOCK = threading.Lock()
_STATUS: dict[str, Any] = {"ok": None, "checked": 0.0, "error": ""}
COLUMNS = ["override_id", "service_date", "route_id", "node_id", "action", "reason", "created_by", "created_at"]
ACTIONS = {"SKIP", "ADD", "RESEQUENCE", "EMERGENCY"}

DDL = """
CREATE TABLE IF NOT EXISTS public.dispatch_overrides (
  override_id BIGSERIAL PRIMARY KEY,
  service_date DATE,
  route_id TEXT,
  node_id TEXT,
  action TEXT,
  reason TEXT,
  created_by TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
)"""


def configured() -> bool:
    s = get_settings()
    return bool(not s.force_mock and s.pg_host)


def _token() -> str:
    with _LOCK:
        if _TOKEN["value"] and time.time() < _TOKEN["exp"]:
            return _TOKEN["value"]
        from server.sql_client import workspace

        w = workspace()
        s = get_settings()
        tok = None
        if s.lakebase_endpoint:
            try:
                tok = w.postgres.generate_database_credential(endpoint=s.lakebase_endpoint).token
            except Exception as e:
                log.warning("generate_database_credential failed, falling back to OAuth token: %s", e)
        if not tok:
            tok = w.config.oauth_token().access_token
        _TOKEN.update(value=tok, exp=time.time() + 40 * 60)
        return tok


def _connect():
    import psycopg

    s = get_settings()
    return psycopg.connect(host=s.pg_host, dbname=s.pg_database, user=s.pg_user, port=s.pg_port,
                           password=_token(), sslmode=s.pg_sslmode, connect_timeout=8,
                           application_name="snb-cash-route")


def _row(r: tuple) -> dict[str, Any]:
    d = dict(zip(COLUMNS, r))
    d["service_date"] = str(d["service_date"]) if d["service_date"] else None
    d["created_at"] = d["created_at"].isoformat() if d.get("created_at") else None
    return d


def list_overrides(route_id: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
    sql = f"SELECT {', '.join(COLUMNS)} FROM public.dispatch_overrides"
    params: list[Any] = []
    if route_id:
        sql += " WHERE route_id = %s"
        params.append(route_id)
    sql += " ORDER BY created_at DESC NULLS LAST, override_id DESC LIMIT %s"
    params.append(limit)
    with _connect() as conn, conn.cursor() as cur:
        try:
            cur.execute(sql, params)
        except Exception as e:
            if "does not exist" not in str(e):
                raise
            conn.rollback()
            cur.execute(DDL)
            conn.commit()
            cur.execute(sql, params)
        return [_row(r) for r in cur.fetchall()]


def insert_override(o: dict[str, Any]) -> dict[str, Any]:
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(
            f"""INSERT INTO public.dispatch_overrides (service_date, route_id, node_id, action, reason, created_by)
                VALUES (%s, %s, %s, %s, %s, %s) RETURNING {', '.join(COLUMNS)}""",
            (o["service_date"], o["route_id"], o["node_id"], o["action"], o.get("reason"), o.get("created_by")),
        )
        row = cur.fetchone()
        conn.commit()
        return _row(row)


def status(force: bool = False) -> dict[str, Any]:
    if not configured():
        return {"ok": False, "error": "PGHOST not set (no Lakebase resource attached)"}
    if not force and _STATUS["ok"] is not None and time.time() - _STATUS["checked"] < 60:
        return {"ok": _STATUS["ok"], "error": _STATUS["error"]}
    try:
        with _connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        _STATUS.update(ok=True, error="", checked=time.time())
    except Exception as e:
        _STATUS.update(ok=False, error=str(e)[:300], checked=time.time())
    return {"ok": _STATUS["ok"], "error": _STATUS["error"]}
