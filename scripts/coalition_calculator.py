#!/usr/bin/env python3
"""Calculadora neutral de coaliciones electorales.

No construye escenarios ni infiere votos: recibe escenarios explícitos y
recalcula D'Hondt con todas las candidaturas presentes en cada circunscripción.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from src.coalition_decision_engine import CoalitionDecisionEngine, CoalitionScenario
from src.coalition_matrix import load_2023_matrix


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Comparación matemática neutral de coaliciones"
    )
    parser.add_argument("--input", required=True, help="JSON con seats y escenarios")
    parser.add_argument("--parties", nargs="+", required=True,
                        help="Universo de candidaturas observadas")
    parser.add_argument("--matrix-2023", action="store_true")
    parser.add_argument("--min-size", type=int, default=2)
    parser.add_argument("--max-size", type=int, default=None)
    parser.add_argument("--max-combinations", type=int, default=100_000)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    source = json.loads(Path(args.input).read_text(encoding="utf-8"))
    if args.matrix_2023:
        matrix = load_2023_matrix()
        source["seats"] = matrix["seats"]
        source["matrix_2023_source"] = matrix["source"]
    scenarios = [
        CoalitionScenario(
            name=s["name"],
            votes=s["votes"],
            weight=float(s.get("weight", 1)),
            assumptions=tuple(s.get("assumptions", ())),
            source=s.get("source", "input_dataset"),
        )
        for s in source["scenarios"]
    ]
    engine = CoalitionDecisionEngine(
        source["seats"],
        source.get("blank"),
        source.get("special"),
    )
    result = engine.analyze_all_coalitions(
        args.parties,
        scenarios,
        min_size=args.min_size,
        max_size=args.max_size,
        max_combinations=args.max_combinations,
    )
    payload = {
        "schema": "NEUTRAL_COALITION_CALCULATOR_V1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "parties_universe": args.parties,
        "source_tier": source.get("source_tier", "UNSPECIFIED"),
        "result": result,
    }
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
