#!/usr/bin/env python3
"""Queen authorization gate.

Workers must call this before any write-capable action. The gate is
conservative: an unknown mission or undeclared write path is denied.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTROL = ROOT / "docs" / "COLMENA_MISSION_CONTROL.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mission-index", type=int, required=True)
    ap.add_argument("--mission", required=True)
    ap.add_argument("--write-path", action="append", default=[])
    args = ap.parse_args()

    data = json.loads(CONTROL.read_text(encoding="utf-8"))
    missions = data.get("missions", [])
    i = args.mission_index
    if i < 0 or i >= len(missions):
        print("DENIED: mission index outside Queen registry")
        return 2
    canonical = str(missions[i]).strip()
    if canonical != args.mission.strip():
        print("DENIED: mission text does not match Queen registry")
        return 2

    # Until a mission has an explicit path allowlist in the registry, it may
    # inspect/validate only. This prevents an unreviewed worker from mutating
    # repository code merely because the swarm was dispatched.
    if args.write_path:
        allow = data.get("write_allowlist", {})
        declared = allow.get(str(i), [])
        if not declared:
            print("DENIED: no Queen-approved write allowlist for this mission")
            return 3
        for raw in args.write_path:
            p = str(Path(raw))
            if not any(p == x or p.startswith(x.rstrip("/") + "/") for x in declared):
                print(f"DENIED: write path outside Queen allowlist: {p}")
                return 3

    print(json.dumps({
        "status": "AUTHORIZED",
        "mission_index": i,
        "mission": canonical,
        "write_authorized": bool(args.write_path),
        "fail_closed": True,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
