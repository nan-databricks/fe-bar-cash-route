"""Map contract rows (gold tables or mock) into the shapes the React pages already render
(Machine, BranchTrack, BranchInput, RouteExecution in frontend/src/types.ts)."""
from __future__ import annotations

import zlib
from datetime import date
from typing import Any

from server import mock

PALETTE = ["#22c55e", "#38bdf8", "#a855f7", "#f2a900", "#ec4899", "#14b8a6", "#f97316", "#84cc16"]
NOW_MIN = 13 * 60 + 20  # demo "current time" for live progress simulation


def _h(s: str) -> int:
    return zlib.crc32(s.encode())


def _clock(m: float) -> str:
    m = int(round(m))
    return f"{m // 60:02d}:{m % 60:02d}"


def _day_label(s: str) -> str:
    try:
        return date.fromisoformat(str(s)[:10]).strftime("%d %b")
    except ValueError:
        return str(s)


def _trend(hist: list[dict], avg: float) -> list[dict]:
    base = abs(avg) * 0.35 + 20_000
    out = []
    for h in hist[-14:]:
        net_out = float(h.get("net_outflow_thb") or 0)
        withdraw = round(base + max(net_out, 0), -3)
        deposit = round(base + max(-net_out, 0), -3)
        out.append({"day": _day_label(h["txn_date"]), "deposit": deposit, "withdraw": withdraw, "net": deposit - withdraw})
    while len(out) < 14:
        out.insert(0, {"day": "—", "deposit": 0, "withdraw": 0, "net": 0})
    return out


_HEALTH = {"CRITICAL": ("Critical", "Very High"), "HIGH": ("Action Needed", "High"), "NORMAL": ("Watch", "Medium")}


def _status(order: dict | None) -> tuple[str, str, str, bool]:
    if not order:
        return "No Action", "Healthy", "Low", False
    health, risk = _HEALTH.get(order["priority"], ("Watch", "Medium"))
    action = "Deliver" if order["action"] == "DELIVER" else "Pickup"
    return action, health, risk, order["priority"] == "CRITICAL"


def machines(nodes: list[dict], hist: dict[str, list[dict]], orders: list[dict]) -> list[dict]:
    by_order = {o["node_id"]: o for o in orders}
    out = []
    for n in nodes:
        if n["node_type"] == "BRANCH":
            continue
        nid = n["node_id"]
        cur = float(n.get("current_cash_thb") or 0)
        fc = float(n.get("forecast_next_day_thb") or n.get("avg_daily_outflow_28d") or 0)
        trend = _trend(hist.get(nid, []), float(n.get("avg_daily_outflow_28d") or fc))
        action, health, risk, emergency = _status(by_order.get(nid))
        seed = _h(nid)
        out.append({
            "id": nid, "nodeType": n["node_type"], "location": n["node_name"], "district": n.get("district") or "",
            "depotId": n.get("depot_id"), "lat": float(n["lat"]), "lng": float(n["lng"]),
            "currentCash": cur, "predictedEod": max(0.0, cur - fc), "cashCapacity": float(n["capacity_thb"]),
            "minCash": float(n.get("min_cash_thb") or 0), "forecastNextDay": fc,
            "confidence": 86 + seed % 12, "action": action, "health": health, "riskLevel": risk,
            "emergency": emergency, "depositToday": trend[-1]["deposit"], "withdrawToday": trend[-1]["withdraw"],
            "denomination": {"b1000": 58 + seed % 9, "b500": 26 + seed % 5, "b100": 11, "b50": 5}
            if n["node_type"] == "ATM" else {"b1000": 49 + seed % 7, "b500": 30, "b100": 15, "b50": 6},
            "trend": trend,
        })
    return out


def branch_tracks(nodes: list[dict], hist: dict[str, list[dict]], orders: list[dict]) -> list[dict]:
    by_order = {o["node_id"]: o for o in orders}
    out = []
    for n in nodes:
        if n["node_type"] != "BRANCH":
            continue
        nid = n["node_id"]
        cap = float(n["capacity_thb"])
        cur = float(n.get("current_cash_thb") or 0)
        fc = float(n.get("forecast_next_day_thb") or n.get("avg_daily_outflow_28d") or 0)
        base = cap * 0.08
        withdraw, deposit = base + max(fc, 0), base + max(-fc, 0)
        action, health, risk, emergency = _status(by_order.get(nid))
        seed = _h(nid)
        out.append({
            "code": nid, "name": n["node_name"], "district": n.get("district") or "", "depotId": n.get("depot_id"),
            "lat": float(n["lat"]), "lng": float(n["lng"]), "currentCash": cur,
            "deposit": round(deposit, -3), "withdraw": round(withdraw, -3), "forecastNet": round(deposit - withdraw, -3),
            "cashCapacity": cap, "minThreshold": float(n.get("min_cash_thb") or 0),
            "action": action, "health": health, "riskLevel": risk, "confidence": 90 + seed % 9, "emergency": emergency,
            "trend": _trend(hist.get(nid, []), float(n.get("avg_daily_outflow_28d") or fc)),
            "denominationGap": {"b1000": round(((seed % 9) - 3) * 450_000, -3), "b500": round(((seed % 7) - 3) * 260_000, -3),
                                "b100": round(((seed % 5) - 3) * 90_000, -3), "b50": round(((seed % 4) - 2) * 40_000, -3)},
        })
    return out


def branch_inputs(nodes: list[dict], depot_id: str = "DEP-KKN-C") -> list[dict]:
    d = mock.DEPOT_BY_ID[depot_id]
    out = [{"code": d["depot_id"], "name": d["depot_name"], "district": d["district"], "lat": d["lat"], "lng": d["lng"],
            "isDepot": True, "cashCapacity": 0, "minThreshold": 0, "openingCash": 0, "predictedInflow": 0, "predictedOutflow": 0}]
    for n in nodes:
        if n["node_type"] != "BRANCH":
            continue
        cap = float(n["capacity_thb"])
        fc = float(n.get("forecast_next_day_thb") or 0)
        base = cap * 0.08
        out.append({
            "code": n["node_id"], "name": n["node_name"], "district": n.get("district") or "",
            "lat": float(n["lat"]), "lng": float(n["lng"]), "cashCapacity": cap,
            "minThreshold": float(n.get("min_cash_thb") or 0), "openingCash": float(n.get("current_cash_thb") or 0),
            "predictedInflow": round(base + max(-fc, 0), -3), "predictedOutflow": round(base + max(fc, 0), -3),
        })
    return out


def route_executions(routes: list[dict]) -> list[dict]:
    vcap = {v["vehicle_id"]: v["cash_capacity_thb"] for v in mock.estate()["vehicles"]}
    out = []
    for i, r in enumerate(routes):
        d = mock.DEPOT_BY_ID.get(r["depot_id"], mock.DEPOTS[0])
        svc = sorted(r.get("stops") or [], key=lambda s: s["stop_seq"])
        in_prog = next((k for k, s in enumerate(svc) if int(s["eta_min"]) >= NOW_MIN), -1)
        stops = [{"seq": 0, "code": "DEPOT", "location": d["depot_name"], "type": "Start", "status": "Completed",
                  "eta": _clock(r.get("start_min") or 480), "lat": d["lat"], "lng": d["lng"], "amount": 0}]
        last_cum = 0.0
        for k, s in enumerate(svc):
            st = "Completed" if in_prog == -1 or k < in_prog else ("In Progress" if k == in_prog else "Pending")
            if st == "Completed":
                last_cum = float(s.get("cum_km") or 0)
            amt = float(s.get("amount_thb") or 0)
            stops.append({"seq": int(s["stop_seq"]), "code": s["node_id"], "location": s.get("node_name") or s["node_id"],
                          "nodeType": s.get("node_type"), "type": "Deliver" if s["action"] == "DELIVER" else "Pickup",
                          "status": st, "eta": _clock(s["eta_min"]), "lat": float(s["lat"]), "lng": float(s["lng"]),
                          "amount": amt if s["action"] == "DELIVER" else -amt})
        stops.append({"seq": len(svc) + 1, "code": "DEPOT", "location": d["depot_name"], "type": "Return",
                      "status": "Completed" if in_prog == -1 else "Pending", "eta": _clock(r.get("end_min") or 1020),
                      "lat": d["lat"], "lng": d["lng"], "amount": 0})
        delivered = float(r.get("cash_delivered_thb") or 0)
        collected = float(r.get("cash_collected_thb") or 0)
        end = int(r.get("end_min") or 1020)
        status = "At Risk" if end > 19 * 60 else ("Delayed" if end > 17 * 60 + 30 else "On Track")
        completed = len(svc) if in_prog == -1 else in_prog
        out.append({
            "routeId": r["route_id"], "truckId": r["vehicle_id"], "planType": r["plan_type"],
            "label": f"{r['depot_id']} · {len(svc)} stops", "status": status, "depot": d["depot_name"],
            "depotId": r["depot_id"], "depotLat": d["lat"], "depotLng": d["lng"], "totalStops": len(svc),
            "completed": completed, "remaining": len(svc) - completed, "distanceKm": float(r.get("km") or 0),
            "distanceLeftKm": round(float(r.get("km") or 0) - last_cum, 1), "etaReturn": _clock(end),
            "vehicleCapacity": max(vcap.get(r["vehicle_id"], 9_000_000.0), round((delivered + collected) * 1.15, -6)),
            "cashOnBoard": delivered + collected, "pickupAmount": collected, "deliveryAmount": delivered,
            "citCostThb": float(r.get("cost_thb") or 0), "durationMin": float(r.get("duration_min") or 0),
            "color": PALETTE[i % len(PALETTE)],
            "path": [[d["lat"], d["lng"]]] + [[float(s["lat"]), float(s["lng"])] for s in svc] + [[d["lat"], d["lng"]]],
            "stops": stops,
        })
    return out
