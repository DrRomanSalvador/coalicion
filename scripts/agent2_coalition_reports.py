#!/usr/bin/env python3
"""Genera informes neutrales y deterministas de coaliciones con la matriz 2023 real."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.integrate_2023_calculator import load_matrix
from src.coalition_reports import (
    DEFAULT_REPORT_IDENTITIES, baseline_seats, build_scenario,
    markdown_all, markdown_executive, pairwise_report, supported_parties,
)

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def main() -> None:
    parser = argparse.ArgumentParser(description="Informes neutrales de coaliciones 2023")
    parser.add_argument("--canonical", default="artifacts/data/election_2023_canonical.json")
    parser.add_argument("--output-dir", default="reports")
    parser.add_argument("--parties", nargs="+", default=None)
    args = parser.parse_args()

    canonical = Path(args.canonical)
    matrix = load_matrix(canonical)
    data = matrix["data"]["constituencies"]
    if len(data) != 52 or sum(c["seats"] for c in data.values()) != 350:
        raise SystemExit("MATRIX_FAIL_CLOSED: 52 circunscripciones y 350 escaños son obligatorios")
    source_sha256 = sha256_file(canonical)

    selected, unsupported = supported_parties(matrix, args.parties or DEFAULT_REPORT_IDENTITIES)
    if len(selected) < 2:
        raise SystemExit("MATRIX_FAIL_CLOSED: menos de dos candidaturas separables")

    results, _ = pairwise_report(matrix, selected)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    all_path = out / "all_coalitions_2023.md"
    exec_path = out / "executive_summary_2023.md"
    json_path = out / "coalition_reports_2023.json"
    all_path.write_text(
        markdown_all(results, unsupported, selected), encoding="utf-8"
    )
    exec_path.write_text(
        markdown_executive(results, unsupported), encoding="utf-8"
    )

    _, _, _, _, observed = build_scenario(matrix)
    payload = {
        "schema": "COALITION_REPORTS_2023_V2",
        "source_tier": matrix["source_tier"],
        "source_sha256": source_sha256,
        "validation": {
            "constituencies": len(data),
            "seats": sum(c["seats"] for c in data.values()),
            "candidate_votes": sum(sum(c["parties"].values()) for c in data.values()),
            "valid_votes": sum(c["valid_votes"] for c in data.values()),
            "selected_identities": selected,
            "unsupported_requested_identities": unsupported,
            "observed_identities": observed,
        },
        "baseline_seats": baseline_seats(matrix),
        "bilateral_count": len(results),
        "invented_votes": False,
        "reports": [str(all_path), str(exec_path)],
    }
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
