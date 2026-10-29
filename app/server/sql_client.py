"""Unity Catalog reads through the SQL Statement Execution API (databricks-sdk, no ODBC driver)."""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import Disposition, Format, StatementState

from server.settings import get_settings

log = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def workspace() -> WorkspaceClient:
    return WorkspaceClient()


def _convert(value: str | None, type_name: str) -> Any:
    if value is None:
        return None
    t = (type_name or "").upper()
    if t in {"INT", "LONG", "SHORT", "BYTE", "BIGINT", "SMALLINT", "TINYINT"}:
        return int(value)
    if t in {"DOUBLE", "FLOAT", "DECIMAL"}:
        return float(value)
    if t == "BOOLEAN":
        return str(value).lower() == "true"
    return value


def query_dicts(statement: str, timeout: str = "30s") -> list[dict[str, Any]]:
    s = get_settings()
    if not s.warehouse_id:
        raise RuntimeError("WAREHOUSE_ID is not configured")
    w = workspace()
    resp = w.statement_execution.execute_statement(
        warehouse_id=s.warehouse_id,
        statement=statement,
        wait_timeout=timeout,
        disposition=Disposition.INLINE,
        format=Format.JSON_ARRAY,
    )
    sid = resp.statement_id
    state = resp.status.state if resp.status else None
    if state in (StatementState.PENDING, StatementState.RUNNING):
        import time

        for _ in range(60):
            time.sleep(1)
            resp = w.statement_execution.get_statement(sid)
            state = resp.status.state if resp.status else None
            if state not in (StatementState.PENDING, StatementState.RUNNING):
                break
    if state != StatementState.SUCCEEDED:
        err = resp.status.error.message if resp.status and resp.status.error else str(state)
        raise RuntimeError(f"Statement failed: {err}")

    cols = [(c.name, c.type_name.value if c.type_name else "STRING") for c in resp.manifest.schema.columns]
    rows: list[list] = list(resp.result.data_array or []) if resp.result else []
    chunk = resp.result.next_chunk_index if resp.result else None
    while chunk is not None:
        part = w.statement_execution.get_statement_result_chunk_n(sid, chunk)
        rows.extend(part.data_array or [])
        chunk = part.next_chunk_index
    return [{name: _convert(v, t) for (name, t), v in zip(cols, r)} for r in rows]
