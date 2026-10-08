#!/usr/bin/env python3
"""Build a reproducible system-state manifest; never invents missing evidence."""
from __future__ import annotations
import json
from datetime import date
from pathlib import Path
from src.political_intelligence import intelligence_snapshot

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "political_intelligence_manifest.json"

def main() -> int:
    snapshot = intelligence_snapshot(as_of=date.today())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": snapshot["status"], "hash": snapshot["hash"], "path": str(OUT)}))
    return 0 if snapshot["gates"]["registry"] and snapshot["gates"]["fail_closed"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
