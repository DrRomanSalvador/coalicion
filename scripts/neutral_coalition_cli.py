#!/usr/bin/env python3
"""CLI neutral para cálculos electorales descriptivos; no recomienda coaliciones."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.neutral_audit import audit_canonical
from src.neutral_coalition import calculate_coalition, enumerate_all_coalition_results

DEFAULT_MATRIX = ROOT / "artifacts/data/election_2023_canonical.json"

def load_matrix(path: Path):
    audit = audit_canonical(path)
    if audit["status"] != "PASS":
        raise SystemExit(f"BLOCKED: {audit["reason"]}")
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data["data"]["constituencies"]
    votes = {name: dict(row["parties"]) for name, row in rows.items()}
    seats = {name: int(row["seats"]) for name, row in rows.items()}
    valid = {name: int(row["valid_votes"]) for name, row in rows.items()}
    blank = {name: int(row.get("blank_votes", 0)) for name, row in rows.items()}
    return data, votes, seats, valid, blank

def result_json(r):
    return {
        "coalition": list(r.coalition),
        "separate_seats": r.separate_seats,
        "coalition_seats": r.coalition_seats,
        "delta": r.delta,
        "separate_by_constituency": r.separate_by_constituency,
        "coalition_by_constituency": r.coalition_by_constituency,
        "delta_by_constituency": r.delta_by_constituency,
    }

def main():
    ap = argparse.ArgumentParser(description="Calculadora electoral neutral y descriptiva")
    ap.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    sub = ap.add_subparsers(dest="command", required=True)

    calc = sub.add_parser("calculate")
    calc.add_argument("--parties", nargs="+", required=True)

    enum = sub.add_parser("enumerate")
    enum.add_argument("--parties", nargs="+", required=True)
    enum.add_argument("--min-size", type=int, default=2)
    enum.add_argument("--max-size", type=int)

    sub.add_parser("audit")

    args = ap.parse_args()
    if args.command == "audit":
        print(json.dumps(audit_canonical(args.matrix), ensure_ascii=False, indent=2))
        return 0

    _, votes, seats, valid, blank = load_matrix(args.matrix)

    if args.command == "calculate":
        print(json.dumps(result_json(calculate_coalition(
            votes, seats, valid, args.parties, blank=blank
        )), ensure_ascii=False, indent=2))
        return 0

    results = []
    for r in enumerate_all_coalition_results(
        votes, seats, valid, args.parties, blank=blank,
        min_size=args.min_size, max_size=args.max_size
    ):
        results.append(result_json(r))
    print(json.dumps({
        "status": "DESCRIPTIVE_ONLY",
        "coalition_count": len(results),
        "scenarios": results,
        "policy": {
            "recommendations": False,
            "ranking_as_best_option": False,
            "party_personalization": False,
            "descriptive_math_only": True,
        },
    }, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
