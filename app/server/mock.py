"""Deterministic SNB (Siam Northeast Bank, fictional) fixtures in the exact contract shapes.

Used whenever Unity Catalog / Lakebase / Model Serving / Genie are unreachable. Estate mirrors
data/01_generate_data.py: 3 depots, 30 vans, 159 branches, 400 ATM + 120 RCM around Khon Kaen.
"""
from __future__ import annotations

import math
import random
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from typing import Any

PLAN_DATE = date(2026, 10, 1)
AS_OF = date(2026, 9, 30)
ROAD_FACTOR = 1.3
SPEED_KMH = 42.0
COST_PER_KM = 28.0
CREW_COST_PER_VAN = 2_400.0
DAY_START = 8 * 60

DEPOTS = [
    {"depot_id": "DEP-KKN-C", "depot_name": "SNB Khon Kaen Central Cash Centre", "district": "Mueang Khon Kaen", "lat": 16.441, "lng": 102.835},
    {"depot_id": "DEP-KKN-N", "depot_name": "SNB Khon Kaen North Cash Centre", "district": "Nam Phong", "lat": 16.708, "lng": 102.766},
    {"depot_id": "DEP-KKN-S", "depot_name": "SNB Khon Kaen South Cash Centre", "district": "Ban Haet", "lat": 16.195, "lng": 102.900},
]
DEPOT_BY_ID = {d["depot_id"]: d for d in DEPOTS}
DISTRICTS = ["Mueang Khon Kaen", "Nam Phong", "Ban Haet", "Chum Phae", "Mancha Khiri", "Phon", "Ban Phai"]


def km(a: dict, b: dict) -> float:
    dlat = (a["lat"] - b["lat"]) * 111.0
    dlng = (a["lng"] - b["lng"]) * 106.5
    return math.hypot(dlat, dlng) * ROAD_FACTOR


def _money(v: float) -> float:
    return float(round(v / 1000.0) * 1000)


@lru_cache(maxsize=1)
def estate() -> dict[str, Any]:
    rng = random.Random(20261001)
    vehicles = [
        {"vehicle_id": f"VAN-{i + 1:02d}", "depot_id": DEPOTS[i % 3]["depot_id"],
         "cash_capacity_thb": float(rng.randint(7, 11) * 1_000_000), "cost_per_km_thb": COST_PER_KM}
        for i in range(30)
    ]
    branches = []
    for i in range(159):
        radius = rng.uniform(2, 59)
        angle = rng.uniform(0, 2 * math.pi)
        lat = 16.43 + radius * math.cos(angle) / 111
        lng = 102.83 + radius * math.sin(angle) / (111 * math.cos(math.radians(16.43)))
        p = {"lat": lat, "lng": lng}
        depot = min(DEPOTS, key=lambda d: km(p, d))
        dist = DISTRICTS[i % len(DISTRICTS)]
        branches.append({
            "node_id": f"SNB-B{i + 1:03d}", "node_type": "BRANCH",
            "node_name": f"SNB {dist} Service Branch {i + 1:03d}", "district": dist,
            "depot_id": depot["depot_id"], "lat": round(lat, 6), "lng": round(lng, 6),
            "capacity_thb": float(rng.randint(9, 19) * 1_000_000),
            "min_cash_thb": float(rng.randint(18, 35) * 100_000),
            "open_min": rng.randint(480, 540), "close_min": rng.randint(960, 1140),
        })
    machines = []
    for i in range(520):
        b = branches[i % len(branches)]
        mtype = "ATM" if i < 400 else "RCM"
        mid = f"SNB-A{i + 1:04d}" if mtype == "ATM" else f"SNB-R{i - 399:04d}"
        machines.append({
            "node_id": mid, "node_type": mtype,
            "node_name": f"{b['district']} {'Retail Point' if i % 3 else 'Mall'} {i + 1:03d}",
            "district": b["district"], "depot_id": b["depot_id"],
            "lat": round(b["lat"] + rng.gauss(0, 0.006), 6), "lng": round(b["lng"] + rng.gauss(0, 0.007), 6),
            "capacity_thb": 2_000_000.0 if mtype == "ATM" else 3_500_000.0,
            "min_cash_thb": 350_000.0 if mtype == "ATM" else 600_000.0,
            "open_min": 0, "close_min": 1440,
        })
    nodes = branches + machines

    status, history, forecast = [], {}, []
    for n in nodes:
        cap, mn = n["capacity_thb"], n["min_cash_thb"]
        if n["node_type"] == "ATM":
            avg = rng.uniform(140_000, 260_000)
        elif n["node_type"] == "RCM":
            avg = rng.uniform(-120_000, 160_000)
        else:
            avg = rng.uniform(-900_000, 1_400_000)
        roll = rng.random()
        if avg > 0 and roll < 0.14:
            current = mn + avg * rng.uniform(0.2, 1.6)
        elif avg < 0 and roll < 0.25:
            current = cap * rng.uniform(0.86, 0.97)
        else:
            current = cap * rng.uniform(0.35, 0.75)
        current = _money(min(cap, max(0, current)))
        status.append({**{k: n[k] for k in ("node_id", "node_type", "node_name", "district", "depot_id", "lat", "lng", "capacity_thb", "min_cash_thb")},
                       "current_cash_thb": current, "avg_daily_outflow_28d": _money(avg),
                       "as_of_date": AS_OF.isoformat()})
        hist = []
        closing = current + avg * 14
        for d in range(14, 0, -1):
            day = AS_OF - timedelta(days=d - 1)
            wf = 0.65 if day.weekday() >= 5 else (1.25 if day.day >= 25 or day.day == 1 else 1.0)
            net = _money(avg * wf * rng.uniform(0.75, 1.25))
            closing = max(0.0, closing - net)
            hist.append({"node_id": n["node_id"], "txn_date": day.isoformat(), "net_outflow_thb": net,
                         "closing_cash_thb": _money(closing)})
        hist[-1]["closing_cash_thb"] = current
        history[n["node_id"]] = hist
        for h in range(1, 8):
            fd = PLAN_DATE + timedelta(days=h - 1)
            wf = 0.65 if fd.weekday() >= 5 else (1.2 if fd.day == 1 else 1.0)
            pred = _money(avg * wf * rng.uniform(0.9, 1.1))
            forecast.append({"node_id": n["node_id"], "node_type": n["node_type"], "forecast_date": fd.isoformat(),
                             "horizon_day": h, "pred_net_outflow_thb": pred,
                             "pred_p80_thb": _money(pred + abs(avg) * 0.18),
                             "model_name": "stable_classic_nan_fe_vm_catalog.snb_cash_ops.cash_demand_forecast",
                             "model_version": "mock", "scored_at": "2026-09-30T23:30:00Z"})
    return {"vehicles": vehicles, "nodes": nodes, "status": status, "history": history, "forecast": forecast}


@lru_cache(maxsize=1)
def orders() -> list[dict[str, Any]]:
    e = estate()
    day1 = {f["node_id"]: f for f in e["forecast"] if f["horizon_day"] == 1}
    node_by = {n["node_id"]: n for n in e["nodes"]}
    out = []
    for s in e["status"]:
        f = day1[s["node_id"]]
        n = node_by[s["node_id"]]
        cur, cap, mn = s["current_cash_thb"], s["capacity_thb"], s["min_cash_thb"]
        p80 = f["pred_p80_thb"]
        if p80 > 0:
            dtc = max(0.0, (cur - mn) / p80)
            if dtc >= 1.6:
                continue
            action, amount = "DELIVER", _money(cap * 0.9 - cur + p80)
            amount = min(amount, cap - cur + p80)
        else:
            if cur < cap * 0.85:
                continue
            dtc = 9.0
            action, amount = "PICKUP", _money(cur - cap * 0.5)
        priority = "CRITICAL" if dtc < 0.5 else ("HIGH" if dtc < 1.0 else "NORMAL")
        is_branch = s["node_type"] == "BRANCH"
        out.append({
            "service_date": PLAN_DATE.isoformat(), "node_id": s["node_id"], "node_type": s["node_type"],
            "node_name": s["node_name"], "depot_id": s["depot_id"], "lat": s["lat"], "lng": s["lng"],
            "action": action, "amount_thb": float(max(amount, 100_000)), "current_cash_thb": cur,
            "days_to_cashout": round(dtc, 2), "priority": priority,
            "tw_start_min": n["open_min"] + 30 if is_branch else 480,
            "tw_end_min": n["close_min"] - 60 if is_branch else 1020,
            "service_min": 25 if is_branch else 15,
        })
    order = {"CRITICAL": 0, "HIGH": 1, "NORMAL": 2}
    out.sort(key=lambda o: (order[o["priority"]], o["days_to_cashout"]))
    return out


def _nn_2opt(depot: dict, stops: list[dict]) -> list[dict]:
    remaining, seq, cur = list(stops), [], depot
    while remaining:
        i = min(range(len(remaining)), key=lambda j: km(cur, remaining[j]))
        cur = remaining.pop(i)
        seq.append(cur)

    def length(s: list[dict]) -> float:
        pts = [depot] + s + [depot]
        return sum(km(pts[i], pts[i + 1]) for i in range(len(pts) - 1))

    improved, guard = True, 0
    while improved and guard < 30:
        improved, guard = False, guard + 1
        for i in range(len(seq) - 1):
            for k in range(i + 1, len(seq)):
                cand = seq[:i] + seq[i:k + 1][::-1] + seq[k + 1:]
                if length(cand) + 1e-6 < length(seq):
                    seq, improved = cand, True
    return seq


def _build_route(plan_type: str, depot: dict, vehicle: dict, seq: list[dict], idx: int) -> tuple[dict, list[dict]]:
    route_id = f"{'OPT' if plan_type == 'OPTIMIZED' else 'BAS'}-{depot['depot_id'][-1]}-{idx:02d}"
    clock, cum, prev = DAY_START, 0.0, depot
    stops, delivered, collected = [], 0.0, 0.0
    for i, o in enumerate(seq, start=1):
        leg = km(prev, o)
        cum += leg
        clock += leg / SPEED_KMH * 60
        clock = max(clock, o.get("tw_start_min", DAY_START))
        stops.append({
            "service_date": PLAN_DATE.isoformat(), "plan_type": plan_type, "route_id": route_id,
            "vehicle_id": vehicle["vehicle_id"], "depot_id": depot["depot_id"], "stop_seq": i,
            "node_id": o["node_id"], "node_type": o["node_type"], "node_name": o["node_name"],
            "action": o["action"], "amount_thb": o["amount_thb"], "eta_min": int(round(clock)),
            "lat": o["lat"], "lng": o["lng"], "cum_km": round(cum, 1),
        })
        clock += o.get("service_min", 20)
        if o["action"] == "DELIVER":
            delivered += o["amount_thb"]
        else:
            collected += o["amount_thb"]
        prev = o
    cum += km(prev, depot)
    clock += km(prev, depot) / SPEED_KMH * 60
    duration = clock - DAY_START
    route = {
        "service_date": PLAN_DATE.isoformat(), "plan_type": plan_type, "route_id": route_id,
        "depot_id": depot["depot_id"], "vehicle_id": vehicle["vehicle_id"], "stops": len(seq),
        "km": round(cum, 1), "duration_min": round(duration, 1), "cash_delivered_thb": delivered,
        "cash_collected_thb": collected, "cost_thb": round(cum * COST_PER_KM + CREW_COST_PER_VAN, 0),
        "start_min": DAY_START, "end_min": int(round(clock)),
    }
    return route, stops


def _sweep(depot: dict, items: list[dict], groups: int) -> list[list[dict]]:
    if not items:
        return []
    items = sorted(items, key=lambda o: math.atan2(o["lat"] - depot["lat"], o["lng"] - depot["lng"]))
    per = math.ceil(len(items) / groups)
    return [items[i:i + per] for i in range(0, len(items), per)]


@lru_cache(maxsize=1)
def plans() -> dict[str, Any]:
    e = estate()
    ords = orders()
    vans_by_depot: dict[str, list[dict]] = {}
    for v in e["vehicles"]:
        vans_by_depot.setdefault(v["depot_id"], []).append(v)
    routes: list[dict] = []
    stops: list[dict] = []

    # OPTIMIZED: forecast-driven orders only, ~10 stops per van, sweep + NN + 2-opt.
    for d in DEPOTS:
        mine = [o for o in ords if o["depot_id"] == d["depot_id"]]
        vans = vans_by_depot[d["depot_id"]]
        n_groups = max(1, min(len(vans), math.ceil(len(mine) / 11)))
        for i, grp in enumerate(_sweep(d, mine, n_groups), start=1):
            r, s = _build_route("OPTIMIZED", d, vans[i - 1], _nn_2opt(d, grp), i)
            routes.append(r)
            stops.extend(s)

    # BASELINE: fixed-cycle plan, every van out, visits each node on its calendar day (by id),
    # unoptimized order; misses some forecast-critical nodes.
    rng = random.Random(7)
    status = e["status"]
    cycle = [s for s in status if int(s["node_id"][-3:]) % 3 == PLAN_DATE.toordinal() % 3]
    critical_ids = {o["node_id"] for o in ords if o["priority"] == "CRITICAL"}
    missed = {nid for nid in critical_ids if rng.random() < 0.55}
    order_by = {o["node_id"]: o for o in ords}
    base_items = []
    for s in cycle:
        o = order_by.get(s["node_id"])
        base_items.append({**s, "action": o["action"] if o else "DELIVER",
                           "amount_thb": o["amount_thb"] if o else _money(s["capacity_thb"] * 0.35),
                           "tw_start_min": DAY_START, "service_min": 25 if s["node_type"] == "BRANCH" else 15})
    base_items = [b for b in base_items if b["node_id"] not in missed]
    for d in DEPOTS:
        mine = [b for b in base_items if b["depot_id"] == d["depot_id"]]
        vans = vans_by_depot[d["depot_id"]]
        for i, grp in enumerate(_sweep(d, mine, len(vans)), start=1):
            r, s = _build_route("BASELINE", d, vans[i - 1], sorted(grp, key=lambda b: b["node_id"]), i)
            routes.append(r)
            stops.extend(s)

    def summary(plan_type: str, risk_nodes: int, sla: float, idle_mult: float) -> dict:
        rs = [r for r in routes if r["plan_type"] == plan_type]
        idle = sum(max(0.0, s["current_cash_thb"] - s["min_cash_thb"] - 3 * max(s["avg_daily_outflow_28d"], 0)) for s in status)
        return {"service_date": PLAN_DATE.isoformat(), "plan_type": plan_type, "routes": len(rs),
                "vehicles_used": len({r["vehicle_id"] for r in rs}), "stops": sum(r["stops"] for r in rs),
                "km": round(sum(r["km"] for r in rs), 1), "duration_hr": round(sum(r["duration_min"] for r in rs) / 60, 1),
                "cost_thb": round(sum(r["cost_thb"] for r in rs), 0), "idle_cash_thb": _money(idle * idle_mult),
                "cashout_risk_nodes": risk_nodes, "sla_pct": sla}

    summ = [
        summary("OPTIMIZED", sum(1 for o in ords if o["priority"] == "CRITICAL" and o["days_to_cashout"] < 0.2), 98.7, 0.62),
        summary("BASELINE", len(missed) + 4, 91.4, 1.0),
    ]
    return {"routes": routes, "stops": stops, "summary": summ}


def nodes() -> list[dict[str, Any]]:
    e = estate()
    day1 = {f["node_id"]: f for f in e["forecast"] if f["horizon_day"] == 1}
    return [{**s, "forecast_next_day_thb": day1[s["node_id"]]["pred_net_outflow_thb"],
             "forecast_p80_thb": day1[s["node_id"]]["pred_p80_thb"]} for s in e["status"]]


def history(node_id: str) -> list[dict[str, Any]]:
    return estate()["history"].get(node_id, [])


def all_history() -> dict[str, list[dict[str, Any]]]:
    return estate()["history"]


def forecast_for(node_id: str) -> list[dict[str, Any]]:
    return [f for f in estate()["forecast"] if f["node_id"] == node_id]


def routes_nested(plan_type: str | None) -> list[dict[str, Any]]:
    p = plans()
    by_route: dict[tuple[str, str], list[dict]] = {}
    for s in p["stops"]:
        by_route.setdefault((s["plan_type"], s["route_id"]), []).append(s)
    out = []
    for r in p["routes"]:
        if plan_type and r["plan_type"] != plan_type:
            continue
        out.append({**r, "stop_count": r["stops"],
                    "stops": sorted(by_route.get((r["plan_type"], r["route_id"]), []), key=lambda x: x["stop_seq"])})
    return out


def model_metrics() -> list[dict[str, Any]]:
    ts = "2026-09-30T22:00:00Z"
    rows = []
    for seg, wape, naive in (("ALL", 0.118, 0.214), ("ATM", 0.104, 0.191), ("RCM", 0.162, 0.287), ("BRANCH", 0.131, 0.233)):
        rows += [{"model_version": "mock", "metric": "WAPE_model", "value": wape, "segment": seg, "logged_at": ts},
                 {"model_version": "mock", "metric": "WAPE_naive", "value": naive, "segment": seg, "logged_at": ts}]
    return rows


_OVERRIDES: list[dict[str, Any]] = [
    {"override_id": 1, "service_date": PLAN_DATE.isoformat(), "route_id": "OPT-C-01", "node_id": "SNB-A0007",
     "action": "SKIP", "reason": "Mall closed for renovation (mock)", "created_by": "ops.lead@snb.example",
     "created_at": "2026-09-30T17:05:00+07:00"},
    {"override_id": 2, "service_date": PLAN_DATE.isoformat(), "route_id": "OPT-N-02", "node_id": "SNB-B044",
     "action": "EMERGENCY", "reason": "Branch reported vault below minimum (mock)", "created_by": "dispatcher@snb.example",
     "created_at": "2026-09-30T18:20:00+07:00"},
]


def list_overrides(route_id: str | None = None) -> list[dict[str, Any]]:
    rows = [o for o in _OVERRIDES if not route_id or o["route_id"] == route_id]
    return sorted(rows, key=lambda o: o["override_id"], reverse=True)


def add_override(o: dict[str, Any]) -> dict[str, Any]:
    row = {**o, "override_id": max((x["override_id"] for x in _OVERRIDES), default=0) + 1,
           "created_at": datetime.now(timezone.utc).isoformat()}
    _OVERRIDES.append(row)
    return row


def genie_answer(question: str) -> dict[str, Any]:
    q = question.lower()
    if "depot" in q or "cost" in q:
        rows: dict[str, dict] = {}
        for r in plans()["routes"]:
            if r["plan_type"] != "OPTIMIZED":
                continue
            d = rows.setdefault(r["depot_id"], {"depot_id": r["depot_id"], "routes": 0, "km": 0.0, "cost_thb": 0.0})
            d["routes"] += 1
            d["km"] = round(d["km"] + r["km"], 1)
            d["cost_thb"] += r["cost_thb"]
        data = list(rows.values())
        text = "Optimized CIT plan for 2026-10-01 by depot (mock answer — Genie space not connected)."
        sql = "SELECT depot_id, COUNT(*) routes, SUM(km) km, SUM(cost_thb) cost_thb FROM gold_routes WHERE plan_type='OPTIMIZED' GROUP BY depot_id"
    else:
        data = [{k: o[k] for k in ("node_id", "node_type", "node_name", "depot_id", "days_to_cashout", "priority")}
                for o in orders()[:10]]
        text = "Top 10 nodes at cash-out risk for 2026-10-01, ordered by days to cash-out (mock answer — Genie space not connected)."
        sql = "SELECT node_id, node_type, node_name, depot_id, days_to_cashout, priority FROM gold_replenishment_orders ORDER BY days_to_cashout LIMIT 10"
    cols = list(data[0].keys()) if data else []
    return {"source": "mock", "conversation_id": "mock-conversation", "message_id": "mock-message",
            "status": "COMPLETED", "text": text, "sql": sql, "columns": cols,
            "rows": [[r[c] for c in cols] for r in data]}
