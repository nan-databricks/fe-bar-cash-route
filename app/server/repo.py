"""Contract-shaped reads: Unity Catalog gold tables first, mock fixtures on any failure.

Every function returns (rows, source) where source is "unity_catalog" or "mock".
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable

from server import mock
from server.settings import get_settings

log = logging.getLogger(__name__)

_CACHE: dict[str, tuple[float, Any, str]] = {}
_LOCK = threading.Lock()
TTL_S = 120
LAST_SOURCE: dict[str, str] = {}
LAST_ERROR: dict[str, str] = {}


def _uc_possible() -> bool:
    s = get_settings()
    return bool(not s.force_mock and s.warehouse_id and s.catalog and s.schema)


def _cached(key: str, live: Callable[[], Any], fallback: Callable[[], Any]) -> tuple[Any, str]:
    now = time.time()
    with _LOCK:
        hit = _CACHE.get(key)
        if hit and now - hit[0] < TTL_S:
            return hit[1], hit[2]
    rows, source = None, "mock"
    if _uc_possible():
        try:
            rows = live()
            if rows:
                source = "unity_catalog"
                LAST_ERROR.pop(key, None)
            else:
                LAST_ERROR[key] = "empty result"
                rows = None
        except Exception as e:  # table missing, no permission, warehouse down...
            LAST_ERROR[key] = str(e)[:300]
            log.warning("UC read %s failed, using mock: %s", key, str(e)[:200])
    if rows is None:
        rows = fallback()
    LAST_SOURCE[key.split(":")[0]] = source
    with _LOCK:
        _CACHE[key] = (now, rows, source)
    return rows, source


def _q(sql: str) -> list[dict[str, Any]]:
    from server.sql_client import query_dicts

    return query_dicts(sql)


def _t(name: str) -> str:
    return get_settings().table(name)


def _date(v: Any) -> str:
    return str(v)[:10] if v is not None else ""


def nodes() -> tuple[list[dict], str]:
    def live():
        try:
            return _q(f"""
                SELECT s.*, f.pred_net_outflow_thb AS forecast_next_day_thb, f.pred_p80_thb AS forecast_p80_thb
                FROM {_t('gold_node_status')} s
                LEFT JOIN (SELECT * FROM {_t('gold_demand_forecast')} WHERE horizon_day = 1) f
                  ON s.node_id = f.node_id
                ORDER BY s.node_type, s.node_id""")
        except RuntimeError as e:
            if "gold_demand_forecast" not in str(e):
                raise
            return _q(f"""SELECT *, avg_daily_outflow_28d AS forecast_next_day_thb, CAST(NULL AS DOUBLE) AS forecast_p80_thb
                          FROM {_t('gold_node_status')} ORDER BY node_type, node_id""")

    rows, src = _cached("nodes", live, mock.nodes)
    for r in rows:
        r["as_of_date"] = _date(r.get("as_of_date"))
    return rows, src


def history() -> tuple[dict[str, list[dict]], str]:
    """Last 14 days of gold_node_daily per node (for trend charts)."""
    def live():
        rows = _q(f"""
            SELECT node_id, CAST(txn_date AS STRING) AS txn_date, net_outflow_thb, closing_cash_thb
            FROM {_t('gold_node_daily')}
            WHERE txn_date > (SELECT MAX(txn_date) FROM {_t('gold_node_daily')}) - INTERVAL 14 DAYS
            ORDER BY node_id, txn_date""")
        out: dict[str, list[dict]] = {}
        for r in rows:
            out.setdefault(r["node_id"], []).append(r)
        return out

    return _cached("history", live, mock.all_history)


def routes(plan_type: str | None) -> tuple[list[dict], str]:
    pt = (plan_type or "").upper()
    if pt not in {"", "OPTIMIZED", "BASELINE"}:
        pt = ""

    def live():
        plan_filter = f"AND plan_type = '{pt}'" if pt else ""
        date_sql = f"(SELECT MAX(service_date) FROM {_t('gold_routes')})"
        rs = _q(f"SELECT * FROM {_t('gold_routes')} WHERE service_date = {date_sql} {plan_filter} ORDER BY plan_type, route_id")
        st = _q(f"SELECT * FROM {_t('gold_route_stops')} WHERE service_date = {date_sql} {plan_filter} ORDER BY plan_type, route_id, stop_seq")
        by: dict[tuple[str, str], list[dict]] = {}
        for x in st:
            x["service_date"] = _date(x.get("service_date"))
            by.setdefault((x["plan_type"], x["route_id"]), []).append(x)
        out = []
        for r in rs:
            r["service_date"] = _date(r.get("service_date"))
            out.append({**r, "stop_count": r.get("stops"), "stops": by.get((r["plan_type"], r["route_id"]), [])})
        return out

    return _cached(f"routes:{pt or 'ALL'}", live, lambda: mock.routes_nested(pt or None))


def summary() -> tuple[list[dict], str]:
    def live():
        rows = _q(f"SELECT * FROM {_t('gold_route_summary')} ORDER BY service_date DESC, plan_type DESC")
        for r in rows:
            r["service_date"] = _date(r.get("service_date"))
        return rows

    return _cached("summary", live, lambda: mock.plans()["summary"])


def orders() -> tuple[list[dict], str]:
    def live():
        rows = _q(f"""SELECT * FROM {_t('gold_replenishment_orders')}
                     WHERE service_date = (SELECT MAX(service_date) FROM {_t('gold_replenishment_orders')})
                     ORDER BY CASE priority WHEN 'CRITICAL' THEN 0 WHEN 'HIGH' THEN 1 ELSE 2 END, days_to_cashout""")
        for r in rows:
            r["service_date"] = _date(r.get("service_date"))
        return rows

    return _cached("orders", live, mock.orders)


def forecast_table(node_id: str) -> tuple[list[dict], str]:
    nid = node_id.replace("'", "")

    def live():
        rows = _q(f"SELECT * FROM {_t('gold_demand_forecast')} WHERE node_id = '{nid}' ORDER BY horizon_day")
        for r in rows:
            r["forecast_date"] = _date(r.get("forecast_date"))
            r["scored_at"] = str(r.get("scored_at") or "")
        return rows

    return _cached(f"forecast:{nid}", live, lambda: mock.forecast_for(nid))


def latest_features(node_id: str) -> tuple[dict | None, str]:
    nid = node_id.replace("'", "")

    def live():
        rows = _q(f"SELECT * FROM {_t('gold_demand_features')} WHERE node_id = '{nid}' ORDER BY txn_date DESC LIMIT 28")
        if rows:
            rows[0]["txn_date"] = _date(rows[0].get("txn_date"))
            rows[0]["_history"] = [float(r["net_outflow_thb"] or 0) for r in rows]
        return rows[:1]

    def fallback():
        hist = mock.history(nid)
        node = next((n for n in mock.nodes() if n["node_id"] == nid), None)
        if not hist or not node:
            return []
        vals = [h["net_outflow_thb"] for h in hist][::-1]
        return [{"node_id": nid, "node_type": node["node_type"], "txn_date": hist[-1]["txn_date"],
                 "lag_1": vals[0], "lag_7": vals[min(6, len(vals) - 1)], "lag_14": vals[-1],
                 "roll7_mean": sum(vals[:7]) / min(7, len(vals)), "roll28_mean": sum(vals) / len(vals),
                 "net_outflow_thb": vals[0], "_history": vals}]

    rows, src = _cached(f"features:{nid}", live, fallback)
    return (rows[0] if rows else None), src


def model_metrics() -> tuple[list[dict], str]:
    def live():
        rows = _q(f"SELECT * FROM {_t('gold_model_metrics')} ORDER BY logged_at DESC LIMIT 200")
        for r in rows:
            r["logged_at"] = str(r.get("logged_at") or "")
        return rows

    return _cached("model_metrics", live, mock.model_metrics)


def uc_live() -> bool:
    return any(v == "unity_catalog" for v in LAST_SOURCE.values())


def clear_cache() -> None:
    with _LOCK:
        _CACHE.clear()
