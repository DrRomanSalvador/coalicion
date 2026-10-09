#!/usr/bin/env python3
"""Build a neutral, explicit baseline decision snapshot from the canonical 2023 matrix.

This is a dated historical baseline only; it is never treated as a 2026 forecast.
"""
from __future__ import annotations
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.rapid_decision_center import decision_snapshot

INPUT = ROOT / "artifacts/data/election_2023_canonical.json"
OUTPUT = ROOT / "artifacts/electoral_decision_snapshot.json"

def main() -> int:
    data = json.loads(INPUT.read_text(encoding="utf-8"))
    rows = data.get("data", {}).get("constituencies", {})
    if len(rows) != 52:
        raise SystemExit(f"FAIL-CLOSED: expected 52 constituencies, got {len(rows)}")
    votes = {name: {str(p): int(v) for p, v in row["parties"].items()} for name, row in rows.items()}
    seats = {name: int(row["seats"]) for name, row in rows.items()}
    blank = {name: int(row["blank_votes"]) for name, row in rows.items()}
    # This is the 2023 historical baseline, not a 2026 projection. Validate
    # its own observed magnitude instead of incorrectly comparing it with
    # the 2026 BOE distribution (Madrid and other magnitudes can differ).
    if sum(seats.values()) != 350:
        raise SystemExit(f"FAIL-CLOSED: 2023 historical matrix must allocate 350 seats, got {sum(seats.values())}")
    for special in ("Ceuta", "Melilla"):
        if special not in rows or seats[special] != 1:
            raise SystemExit(f"FAIL-CLOSED: invalid 2023 historical magnitude for {special}")
    special_rules = {"Ceuta": "Ceuta", "Melilla": "Melilla"}
    snapshot = decision_snapshot(
        votes, seats, blank,
        special_by_constituency=special_rules,
        strict_territory=False,
    )
    snapshot["baseline"] = {
        "election_date": "2023-07-23",
        "source_tier": data.get("source_tier"),
        "source_scope": "historical_baseline_only",
        "forecast_2026": False,
        "territorial_extrapolation": False,
    }
    snapshot["limitations"].append("Este snapshot es un baseline histórico 23J; no representa una predicción ni un dato 2026.")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps({"status": snapshot["status"], "path": str(OUTPUT.relative_to(ROOT)), "baseline": snapshot["baseline"]}, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
