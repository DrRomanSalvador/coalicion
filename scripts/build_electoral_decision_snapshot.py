#!/usr/bin/env python3
"""Build a neutral, explicit baseline decision snapshot from the canonical 2023 matrix.

This is a dated historical baseline only; it is never treated as a 2026 forecast.
"""
from __future__ import annotations
import json
from pathlib import Path
from src.rapid_decision_center import decision_snapshot

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "artifacts/data/election_2023_canonical.json"
OUTPUT = ROOT / "artifacts/electoral_decision_snapshot.json"

def main() -> int:
    data = json.loads(INPUT.read_text(encoding="utf-8"))
    rows = data.get("data", {}).get("constituencies", {})
    if len(rows) != 52:
        raise SystemExit(f"FAIL-CLOSED: expected 52 constituencies, got {len(rows)}")
    votes = {name: {str(p): int(v) for p, v in row["parties"].items()} for name, row in rows.items()}
    seats = {name: int(row["seats"]) for name, row in rows.items()}
    blank = {name: int(row.get("blank_votes", 0)) for name, row in rows.items()}
    snapshot = decision_snapshot(votes, seats, blank, strict_territory=True)
    snapshot["baseline"] = {
        "election_date": "2023-07-23",
        "source_tier": data.get("source_tier"),
        "source_scope": "historical_baseline_only",
        "forecast_2026": False,
        "territorial_extrapolation": False,
    }
    snapshot["limitations"].append("Este snapshot es un baseline histórico 23J; no representa una predicción ni un dato 2026.")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": snapshot["status"], "path": str(OUTPUT.relative_to(ROOT)), "baseline": snapshot["baseline"]}, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
