"""Genie Conversation API client for the "SNB Cash Ops Assistant" space."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from server import mock
from server.settings import get_settings

log = logging.getLogger(__name__)
LAST_ERROR: dict[str, str] = {}


def configured() -> bool:
    s = get_settings()
    return bool(not s.force_mock and s.genie_space_id)


def _query_result(w, space_id: str, conv_id: str, msg_id: str, att_id: str) -> tuple[list[str], list[list]]:
    res = w.genie.get_message_attachment_query_result(space_id, conv_id, msg_id, att_id)
    sr = res.statement_response
    if not sr or not sr.manifest or not sr.manifest.schema:
        return [], []
    cols = [c.name for c in sr.manifest.schema.columns or []]
    rows = (sr.result.data_array if sr.result else None) or []
    return cols, rows[:200]


def ask(question: str, conversation_id: str | None = None) -> dict[str, Any]:
    if not configured():
        return {**mock.genie_answer(question), "note": "GENIE_SPACE_ID not set — mock answer"}
    s = get_settings()
    try:
        from server.sql_client import workspace

        w = workspace()
        timeout = timedelta(minutes=3)
        if conversation_id and not conversation_id.startswith("mock"):
            msg = w.genie.create_message_and_wait(s.genie_space_id, conversation_id, question, timeout=timeout)
        else:
            msg = w.genie.start_conversation_and_wait(s.genie_space_id, question, timeout=timeout)
        texts, sql, cols, rows = [], None, [], []
        for att in msg.attachments or []:
            if att.text and att.text.content:
                texts.append(att.text.content)
            if att.query:
                sql = att.query.query
                if att.query.description:
                    texts.append(att.query.description)
                if att.attachment_id:
                    cols, rows = _query_result(w, s.genie_space_id, msg.conversation_id, msg.message_id, att.attachment_id)
        LAST_ERROR.pop("genie", None)
        return {"source": "genie", "conversation_id": msg.conversation_id, "message_id": msg.message_id,
                "status": msg.status.value if msg.status else "COMPLETED",
                "text": "\n\n".join(texts) or (msg.error.error if msg.error else ""),
                "sql": sql, "columns": cols, "rows": rows}
    except Exception as e:
        LAST_ERROR["genie"] = str(e)[:300]
        log.warning("Genie ask failed, mock answer: %s", str(e)[:200])
        return {**mock.genie_answer(question), "note": f"Genie unavailable: {str(e)[:160]}"}
