#!/usr/bin/env python3
"""Fail-closed dispatcher for the atomic COALICION mission swarm.

This is the executable orchestration layer. It does not pretend to create
independent LLMs: it creates one isolated CI worker slot per atomic mission,
with a Queen Gate authorization step before any write-capable operation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTROL = ROOT / "docs" / "COLMENA_MISSION_CONTROL.json"


def load() -> dict:
    data = json.loads(CONTROL.read_text(encoding="utf-8"))
    missions = data.get("missions")
    if not isinstance(missions, list) or not missions:
        raise SystemExit("FAIL_CLOSED: no atomic missions")
    # Repeated titles are distinct atomic missions; identity is ordinal-bound.
    return data


def mission_id(index: int, text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
    return f"M{index + 1:04d}-{digest}"


def build(data: dict) -> list[dict]:
    result = []
    for i, raw in enumerate(data["missions"]):
        text = str(raw).strip()
        if not text:
            raise SystemExit(f"FAIL_CLOSED: empty mission at index {i}")
        result.append({
            "index": i,
            "id": mission_id(i, text),
            "mission": text,
            "write_approved": False,
            "status": "QUEUED",
        })
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--matrix", action="store_true")
    ap.add_argument("--validate", action="store_true")
    args = ap.parse_args()
    data = load()
    missions = build(data)
    payload = {
        "schema": "COLMENA_DISPATCH_V1",
        "mode": data.get("mode"),
        "worker_write_gate": data.get("worker_write_gate"),
        "count": len(missions),
        "missions": missions,
        "fail_closed": True,
    }
    if args.validate:
        print(json.dumps({"status": "PASS", "count": len(missions)}, ensure_ascii=False))
    else:
        print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
