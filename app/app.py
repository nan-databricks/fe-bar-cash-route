"""FastAPI entry point for SNB Cash Logistics (Databricks App `snb-cash-route`).

Contract endpoints (contract/tables.yaml `app_api`) read Unity Catalog gold tables through the
attached SQL warehouse, Lakebase Postgres for dispatch overrides, the `snb-cash-forecast`
serving endpoint and the Genie space. Every endpoint falls back to deterministic SNB mock
fixtures (server/mock.py) when a dependency is unreachable; /api/health reports which are live.
"""
from __future__ import annotations

import logging
import os
from datetime import date
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from server import adapters, genie, lakebase, mock, repo, serving
from server.settings import get_settings

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("snb-cash-route")

app = FastAPI(title="SNB Cash Logistics")


# ------------------------------------------------------------------ health
@app.get("/api/health")
def health(deep: bool = Query(default=True)):
    s = get_settings()
    if deep:
        repo.summary()
        repo.nodes()
    lb = lakebase.status() if deep else {"ok": False, "error": "skipped"}
    endpoint_state = "not_configured"
    if s.serving_endpoint and not s.force_mock:
        try:
            from server.sql_client import workspace

            ep = workspace().serving_endpoints.get(s.serving_endpoint)
            ready = ep.state.ready.value if ep.state and ep.state.ready else "UNKNOWN"
            endpoint_state = f"{ready}"
        except Exception as e:
            endpoint_state = f"unreachable: {str(e)[:120]}"
    sources = {k: v for k, v in sorted(repo.LAST_SOURCE.items())}
    return {
        "status": "ok",
        "app": "snb-cash-route",
        "catalog": s.catalog,
        "schema": s.schema,
        "warehouse_id": s.warehouse_id,
        "plan_date": s.plan_date,
        "unity_catalog": repo.uc_live(),
        "lakebase": bool(lb.get("ok")),
        "endpoint": s.serving_endpoint,
        "endpoint_state": endpoint_state,
        "genie": genie.configured(),
        "genie_space_id": s.genie_space_id or None,
        "force_mock": s.force_mock,
        "sources": sources,
        "errors": {**{f"uc.{k}": v for k, v in repo.LAST_ERROR.items()},
                   **({"lakebase": lb["error"]} if lb.get("error") else {}),
                   **{f"serving.{k}": v for k, v in serving.LAST_ERROR.items()},
                   **{f"genie.{k}": v for k, v in genie.LAST_ERROR.items()}},
    }


# ------------------------------------------------------------------ contract endpoints
@app.get("/api/nodes")
def api_nodes(node_type: str | None = None):
    rows, src = repo.nodes()
    if node_type:
        rows = [r for r in rows if r["node_type"] == node_type.upper()]
    return {"source": src, "count": len(rows), "nodes": rows}


@app.get("/api/routes")
def api_routes(plan_type: str | None = Query(default=None, description="OPTIMIZED | BASELINE")):
    rows, src = repo.routes(plan_type)
    return {"source": src, "plan_type": (plan_type or "ALL").upper(), "count": len(rows), "routes": rows}


@app.get("/api/summary")
def api_summary():
    rows, src = repo.summary()
    return {"source": src, "summary": rows}


@app.get("/api/orders")
def api_orders():
    rows, src = repo.orders()
    return {"source": src, "count": len(rows), "orders": rows}


class ForecastIn(BaseModel):
    node_id: str


@app.post("/api/forecast")
def api_forecast(body: ForecastIn):
    try:
        return serving.reforecast(body.node_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown node_id {body.node_id}")


class OverrideIn(BaseModel):
    service_date: str | None = None
    route_id: str
    node_id: str
    action: str = Field(description="SKIP | ADD | RESEQUENCE | EMERGENCY")
    reason: str | None = None
    created_by: str | None = None


@app.get("/api/overrides")
def api_overrides_list(route_id: str | None = None):
    if lakebase.configured():
        try:
            return {"source": "lakebase", "overrides": lakebase.list_overrides(route_id)}
        except Exception as e:
            log.warning("Lakebase read failed: %s", e)
            return {"source": "mock", "error": str(e)[:200], "overrides": mock.list_overrides(route_id)}
    return {"source": "mock", "overrides": mock.list_overrides(route_id)}


@app.post("/api/overrides")
def api_overrides_create(body: OverrideIn, request: Request):
    action = body.action.upper()
    if action not in lakebase.ACTIONS:
        raise HTTPException(status_code=400, detail=f"action must be one of {sorted(lakebase.ACTIONS)}")
    row: dict[str, Any] = {
        "service_date": body.service_date or get_settings().plan_date,
        "route_id": body.route_id, "node_id": body.node_id, "action": action, "reason": body.reason,
        "created_by": body.created_by or request.headers.get("x-forwarded-email") or "local-user",
    }
    date.fromisoformat(row["service_date"])
    if lakebase.configured():
        try:
            return {"source": "lakebase", "override": lakebase.insert_override(row)}
        except Exception as e:
            log.warning("Lakebase write failed: %s", e)
            return {"source": "mock", "error": str(e)[:200], "override": mock.add_override(row)}
    return {"source": "mock", "override": mock.add_override(row)}


class GenieIn(BaseModel):
    question: str
    conversation_id: str | None = None


@app.post("/api/genie/ask")
def api_genie(body: GenieIn):
    if not body.question.strip():
        raise HTTPException(status_code=400, detail="question is required")
    return genie.ask(body.question.strip(), body.conversation_id)


# ------------------------------------------------------------------ UI-shaped endpoints (existing pages)
@app.get("/api/machines")
def api_machines():
    nodes, src = repo.nodes()
    hist, _ = repo.history()
    orders, _ = repo.orders()
    return {"source": src, "businessDate": get_settings().plan_date, "machines": adapters.machines(nodes, hist, orders)}


@app.get("/api/branches")
def api_branches():
    nodes, src = repo.nodes()
    hist, _ = repo.history()
    orders, _ = repo.orders()
    return {"source": src, "businessDate": get_settings().plan_date, "branches": adapters.branch_tracks(nodes, hist, orders)}


@app.get("/api/branch-inputs")
def api_branch_inputs():
    nodes, src = repo.nodes()
    return {"source": src, "branches": adapters.branch_inputs(nodes)}


@app.get("/api/route-executions")
def api_route_executions(plan_type: str = Query(default="OPTIMIZED")):
    rows, src = repo.routes(plan_type)
    return {"source": src, "plan_type": plan_type.upper(), "routes": adapters.route_executions(rows)}


@app.get("/api/model-metrics")
def api_model_metrics():
    rows, src = repo.model_metrics()
    return {"source": src, "metrics": rows}


@app.post("/api/cache/clear")
def api_cache_clear():
    repo.clear_cache()
    return {"status": "cleared"}


# ------------------------------------------------------------------ SPA
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend", "dist")

if os.path.isdir(FRONTEND_DIR):
    assets_dir = os.path.join(FRONTEND_DIR, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404)
        candidate = os.path.join(FRONTEND_DIR, full_path)
        if full_path and os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
