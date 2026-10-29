"""7-day re-forecast for one node via the `snb-cash-forecast` Model Serving endpoint."""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from server import mock, repo
from server.settings import get_settings

log = logging.getLogger(__name__)

FEATURES = ["node_type", "dow", "dom", "is_weekend", "is_holiday", "is_payday",
            "lag_1", "lag_7", "lag_14", "roll7_mean", "roll28_mean"]
HOLIDAYS = {"2026-10-13": "Memorial Day", "2026-10-23": "Chulalongkorn Day"}
LAST_ERROR: dict[str, str] = {}


def _history_desc(node_id: str, feat: dict) -> list[float]:
    """Most-recent-first daily net outflow values (actuals)."""
    if feat.get("_history"):
        return list(feat["_history"])
    hist, _ = repo.history()
    vals = [float(h["net_outflow_thb"]) for h in hist.get(node_id, [])][::-1]
    if not vals:
        vals = [float(feat.get("net_outflow_thb") or feat.get("lag_1") or 0.0)]
    return vals


def build_records(node_id: str, feat: dict, start: date) -> list[dict[str, Any]]:
    actual = _history_desc(node_id, feat)
    proxy = float(feat.get("roll7_mean") or (sum(actual[:7]) / max(1, len(actual[:7]))))
    roll28 = float(feat.get("roll28_mean") or proxy)
    last = date.fromisoformat(str(feat.get("txn_date") or (start - timedelta(days=1)))[:10])

    def value_at(d: date) -> float:
        idx = (last - d).days
        if 0 <= idx < len(actual):
            return actual[idx]
        return proxy

    records = []
    for h in range(1, 8):
        t = start + timedelta(days=h - 1)
        window7 = [value_at(t - timedelta(days=k)) for k in range(1, 8)]
        records.append({
            "node_type": feat.get("node_type") or "ATM",
            "dow": t.isoweekday(), "dom": t.day,
            "is_weekend": t.isoweekday() >= 6,
            "is_holiday": t.isoformat() in HOLIDAYS,
            "is_payday": t.day >= 25 or t.day == 1,
            "lag_1": round(value_at(t - timedelta(days=1)), 2),
            "lag_7": round(value_at(t - timedelta(days=7)), 2),
            "lag_14": round(value_at(t - timedelta(days=14)), 2),
            "roll7_mean": round(sum(window7) / 7, 2),
            "roll28_mean": round(roll28, 2),
        })
    return records


def _parse_predictions(preds: Any) -> list[tuple[float, float]]:
    out = []
    if isinstance(preds, dict):  # column-oriented
        p = preds.get("pred_net_outflow_thb") or []
        q = preds.get("pred_p80_thb") or p
        return [(float(a), float(b)) for a, b in zip(p, q)]
    for p in preds or []:
        if isinstance(p, dict):
            point = float(p.get("pred_net_outflow_thb", p.get("prediction", 0.0)))
            out.append((point, float(p.get("pred_p80_thb", point))))
        elif isinstance(p, (list, tuple)):
            out.append((float(p[0]), float(p[1] if len(p) > 1 else p[0])))
        else:
            out.append((float(p), float(p)))
    return out


def reforecast(node_id: str) -> dict[str, Any]:
    s = get_settings()
    start = date.fromisoformat(s.plan_date)
    feat, feat_src = repo.latest_features(node_id)
    if feat is None:
        raise KeyError(node_id)
    records = build_records(node_id, feat, start)
    history = [{"date": (start - timedelta(days=i + 1)).isoformat(), "net_outflow_thb": v}
               for i, v in enumerate(_history_desc(node_id, feat)[:14])][::-1]

    source, preds = "mock", None
    if not s.force_mock and s.serving_endpoint:
        try:
            from server.sql_client import workspace

            resp = workspace().serving_endpoints.query(name=s.serving_endpoint, dataframe_records=records)
            preds = _parse_predictions(resp.predictions)
            if len(preds) == len(records):
                source = "serving_endpoint"
                LAST_ERROR.pop("serving", None)
            else:
                preds = None
        except Exception as e:
            LAST_ERROR["serving"] = str(e)[:300]
            log.warning("Serving endpoint %s failed: %s", s.serving_endpoint, str(e)[:200])

    if preds is None:
        rows, tsrc = repo.forecast_table(node_id)
        if not rows:
            rows = mock.forecast_for(node_id)
        preds = [(float(r["pred_net_outflow_thb"]), float(r["pred_p80_thb"])) for r in rows[:7]]
        source = "forecast_table" if tsrc == "unity_catalog" else "mock"

    forecast = [{"forecast_date": (start + timedelta(days=i)).isoformat(), "horizon_day": i + 1,
                 "pred_net_outflow_thb": round(p, 0), "pred_p80_thb": round(q, 0)}
                for i, (p, q) in enumerate(preds)]
    return {"node_id": node_id, "node_type": feat.get("node_type"), "source": source,
            "features_source": feat_src, "endpoint": s.serving_endpoint,
            "request": {"dataframe_records": records}, "forecast": forecast, "history": history}
