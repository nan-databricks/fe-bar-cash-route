#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["databricks-sdk>=0.30"]
# ///
"""Ask the live SNB Cash Ops Assistant space and print TEXT answers.

Usage (from repo root or genie/):
  python3 genie/run_benchmarks.py
  python3 genie/run_benchmarks.py --space-id <id>
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import timedelta
from pathlib import Path

from databricks.sdk import WorkspaceClient

QUESTIONS = [
    "Which nodes run out of cash in the next 3 days if we do nothing?",
    "How much idle cash is sitting in each depot as of 2026-09-30?",
    "How many vans did the fixed-cycle plan use on 2026-09-30?",
    "Which districts have the highest cash-out risk?",
    "What is CIT cost of optimized vs baseline for 2026-10-01?",
    "Show forecast WAPE by node type",
]


def extract(msg) -> dict:
    texts, sql = [], None
    for att in msg.attachments or []:
        if att.text and att.text.content:
            texts.append(att.text.content)
        if att.query:
            sql = att.query.query
            if att.query.description:
                texts.append(att.query.description)
    err = ""
    if msg.error:
        err = msg.error.error if hasattr(msg.error, "error") else str(msg.error)
    return {
        "conversation_id": msg.conversation_id,
        "message_id": msg.message_id,
        "status": msg.status.value if msg.status else "",
        "sql": sql,
        "text": "\n\n".join(texts) or err,
        "error": err,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--space-id", default="")
    p.add_argument("--profile", default="nan-demo")
    args = p.parse_args()
    w = WorkspaceClient(profile=args.profile)
    space_id = args.space_id.strip()
    if not space_id:
        for s in w.genie.list_spaces().spaces or []:
            if s.title == "SNB Cash Ops Assistant":
                space_id = s.space_id
                break
    if not space_id:
        sys.exit("space not found")

    out = []
    for q in QUESTIONS:
        print("ASK:", q, flush=True)
        try:
            msg = w.genie.start_conversation_and_wait(
                space_id, q, timeout=timedelta(minutes=4)
            )
            rec = extract(msg)
        except Exception as exc:
            rec = {
                "conversation_id": "",
                "message_id": "",
                "status": "ERROR",
                "sql": None,
                "text": str(exc),
                "error": str(exc),
            }
        rec["question"] = q
        out.append(rec)
        print("  status", rec["status"], "conv", rec["conversation_id"], flush=True)
        time.sleep(2)

    print(json.dumps(out, indent=2))
    dest = Path(__file__).resolve().parents[1] / "evidence" / "genie_benchmarks.txt"
    dest.parent.mkdir(exist_ok=True)
    lines = [
        "SNB Cash Ops Assistant — live Genie benchmark pack",
        f"space_id: {space_id}",
        f"url: {w.config.host.rstrip('/')}/genie/rooms/{space_id}",
        "",
    ]
    for i, rec in enumerate(out, 1):
        lines += [
            f"{'=' * 72}",
            f"Q{i}. {rec['question']}",
            f"conversation_id: {rec.get('conversation_id') or '(none)'}",
            f"message_id: {rec.get('message_id') or '(none)'}",
            f"status: {rec.get('status')}",
            "SQL:",
            rec.get("sql") or "(no SQL attachment)",
            "",
            "ANSWER:",
            rec.get("text") or "(empty)",
            "",
        ]
    dest.write_text("\n".join(lines))
    print("wrote", dest)


if __name__ == "__main__":
    main()
