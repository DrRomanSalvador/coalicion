#!/usr/bin/env python3
"""Integra la matriz 2023 canónica en la calculadora electoral neutral."""
from __future__ import annotations

import argparse
import json
import unicodedata
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.coalition_decision_engine import CoalitionDecisionEngine, CoalitionScenario


def normalize_label(value: str) -> str:
    text = unicodedata.normalize("NFKD", value)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(text.casefold().replace("-", " ").replace("/", " ").split())


ALIASES = {
    "valencia": "valencia/valència",
    "valencia valencia": "valencia/valència",
    "pais valenciano": "valencia/valència",
    "pais valencia": "valencia/valència",
    "valencia valencia": "valencia/valència",
    "castellon castello": "castellón/castelló",
    "castellon": "castellón/castelló",
    "castello": "castellón/castelló",
    "araba alava": "araba/álava",
    "araba": "araba/álava",
    "alava": "araba/álava",
    "a coruna": "a coruña",
    "la coruna": "a coruña",
    "gipuzkoa": "gipuzkoa",
    "guipuzcoa": "gipuzkoa",
    "bizkaia": "bizkaia",
    "vizcaya": "bizkaia",
    "balears illes": "balears, illes",
    "illes balears": "balears, illes",
    "baleares": "balears, illes",
}


def canonical_constituency(name: str, known: set[str]) -> str:
    key = normalize_label(name)
    target = ALIASES.get(key, name)
    normalized = {normalize_label(k): k for k in known}
    target_key = normalize_label(target)
    if target_key in normalized:
        return normalized[target_key]
    if key in normalized:
        return normalized[key]
    raise ValueError(f"CONSTITUENCY_UNKNOWN:{name}")


def load_matrix(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"MATRIX_NOT_AVAILABLE:{path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "ELECTION_2023_CONSTITUENCY_MATRIX_V1":
        raise ValueError("MATRIX_SCHEMA_INVALID")
    if data.get("source_tier") != "SECONDARY_REPLICA_VERIFIED":
        raise ValueError("MATRIX_SOURCE_TIER_INVALID")

    constituencies = data.get("data", {}).get("constituencies", {})
    if len(constituencies) != 52:
        raise ValueError(f"MATRIX_CONSTITUENCIES_INVALID:{len(constituencies)}")
    if sum(c.get("seats", 0) for c in constituencies.values()) != 350:
        raise ValueError("MATRIX_SEATS_INVALID")

    candidate_votes = sum(
        sum(c.get("parties", {}).values()) for c in constituencies.values()
    )
    if candidate_votes != 24_487_414:
        raise ValueError(f"MATRIX_CANDIDATE_VOTES_INVALID:{candidate_votes}")

    for name, c in constituencies.items():
        parties = c.get("parties", {})
        if not parties or any(
            isinstance(v, bool) or not isinstance(v, int) or v < 0
            for v in parties.values()
        ):
            raise ValueError(f"MATRIX_PARTIES_INVALID:{name}")
        if c.get("valid_votes") != sum(parties.values()) + c.get("blank_votes", 0):
            raise ValueError(f"MATRIX_VALID_ARITHMETIC_INVALID:{name}")

    return data


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--canonical",
        default="artifacts/data/election_2023_canonical.json",
    )
    parser.add_argument(
        "--output",
        default="artifacts/data/coalition_calculator_integration.json",
    )
    args = parser.parse_args()

    data = load_matrix(Path(args.canonical))
    raw = data["data"]["constituencies"]
    known = set(raw)

    normalized = {}
    for name, c in raw.items():
        canonical = canonical_constituency(name, known)
        if canonical in normalized:
            raise ValueError(f"MATRIX_ALIAS_COLLISION:{name}->{canonical}")
        normalized[canonical] = c

    seats = {name: c["seats"] for name, c in normalized.items()}
    votes = {name: c["parties"] for name, c in normalized.items()}
    blanks = {name: c["blank_votes"] for name, c in normalized.items()}

    engine = CoalitionDecisionEngine(seats, blanks)
    baseline = engine._allocate
    national_seats = {}
    constituency_seats = {}
    for name, row in votes.items():
        allocation = baseline(row, name)
        constituency_seats[name] = allocation.seats
        for party, seats_won in allocation.seats.items():
            national_seats[party] = national_seats.get(party, 0) + seats_won

    payload = {
        "schema": "COALITION_CALCULATOR_2023_INTEGRATION_V1",
        "source_tier": data["source_tier"],
        "source_matrix": str(Path(args.canonical)),
        "validation": {
            "constituencies": len(votes),
            "seats": sum(seats.values()),
            "candidate_votes": sum(sum(r.values()) for r in votes.values()),
            "valid_votes": sum(c["valid_votes"] for c in normalized.values()),
            "blank_votes": sum(blanks.values()),
            "expected_candidate_votes": 24_487_414,
            "expected_valid_votes": 24_688_087,
            "normalization_aliases_checked": [
                "Valencia",
                "València",
                "País Valencià",
                "Castellón/Castelló",
                "Araba/Álava",
                "Balears, Illes",
            ],
        },
        "baseline_2023": {
            "national_seats": dict(sorted(national_seats.items())),
            "constituency_seats": constituency_seats,
        },
        "calculator": {
            "engine": "CoalitionDecisionEngine",
            "dhondt_recalculated": True,
            "all_observed_candidates_preserved": True,
            "invented_votes": False,
        },
    }

    if (
        payload["validation"]["candidate_votes"] != 24_487_414
        or payload["validation"]["valid_votes"] != 24_688_087
        or sum(national_seats.values()) != 350
    ):
        raise RuntimeError("INTEGRATION_FAIL_CLOSED")

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
