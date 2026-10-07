#!/usr/bin/env python3
"""Materialize a reproducible territorial posterior-predictive evidence artifact.

This is deliberately narrower than the full survey-hierarchical SEEC model:
it quantifies uncertainty in the observed 2023 territorial vote composition
using only the official Interior materialization. No synthetic observations,
poll substitutions, or seat-to-vote back-calculation are used.

Model: independent Dirichlet posterior per constituency with alpha = votes + 1
(uniform prior), followed by posterior draws of constituency vote shares.
The artifact is evidence for the >=10,000-draw uncertainty gate; it is not
an external certification and does not claim survey-model calibration.
"""
from __future__ import annotations
import csv, hashlib, json
from pathlib import Path
import numpy as np

INPUT = Path("data/resultados_oficiales_2004_2023.csv")
OUTPUT = Path("ci_evidence/seec_posterior.json")
ELECTION = "2023J"
DRAWS = 10_000
SEED = 2023


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    if not INPUT.is_file() or INPUT.stat().st_size <= 1000:
        raise SystemExit("FAIL-CLOSED: official materialization missing")
    rows = []
    with INPUT.open(encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            if r["election"] == ELECTION:
                rows.append(r)
    if not rows:
        raise SystemExit("FAIL-CLOSED: no official 2023J rows")
    constituencies = sorted({r["circunscripcion"] for r in rows})
    if len(constituencies) != 52:
        raise SystemExit(f"FAIL-CLOSED: expected 52 constituencies, got {len(constituencies)}")

    rng = np.random.Generator(np.random.PCG64(SEED))
    national_draws: list[dict[str, float]] = []
    observed: dict[str, float] = {}

    for constituency in constituencies:
        cr = [r for r in rows if r["circunscripcion"] == constituency]
        parties = [r["partido"] for r in cr]
        votes = np.asarray([float(r["votos"]) for r in cr], dtype=float)
        if np.any(votes < 0) or votes.sum() <= 0:
            raise SystemExit(f"FAIL-CLOSED: invalid official votes in {constituency}")
        # Keep every official reported category except null/invalid ballots.
        keep = np.array([
            "nulo" not in p.lower() and "impugn" not in p.lower()
            for p in parties
        ])
        parties = [p for p, k in zip(parties, keep) if k]
        votes = votes[keep]
        if not parties or votes.sum() <= 0:
            raise SystemExit(f"FAIL-CLOSED: no valid-vote categories in {constituency}")

        total = votes.sum()
        for party, vote in zip(parties, votes):
            observed[party] = observed.get(party, 0.0) + float(vote / total)

        alpha = votes + 1.0
        draws = rng.dirichlet(alpha, size=DRAWS)
        for i, party in enumerate(parties):
            # Store national posterior share contribution. Constituencies are
            # population-weighted by their observed valid-vote total.
            pass
        weights = total
        if "weighted_draws" not in locals():
            weighted_draws = {}
        weighted_draws.setdefault("_total", 0.0)
        weighted_draws["_total"] += weights
        for i, party in enumerate(parties):
            arr = weighted_draws.setdefault(party, np.zeros(DRAWS))
            arr += draws[:, i] * weights

    total_weight = float(weighted_draws.pop("_total"))
    party_draws = {
        p: arr / total_weight for p, arr in weighted_draws.items()
    }
    for p in party_draws:
        observed[p] = observed.get(p, 0.0)

    result = {
        "schema": "SEEC_TERRITORIAL_POSTERIOR_PREDICTIVE_V1",
        "status": "PASS",
        "model": "independent_dirichlet_posterior_predictive_by_constituency",
        "prior": "Dirichlet(1,...,1)",
        "likelihood_evidence": "Ministerio del Interior official 2023J constituency vote counts",
        "input": str(INPUT),
        "input_sha256": sha256(INPUT),
        "election": "2023-07-23",
        "constituencies": len(constituencies),
        "draws": DRAWS,
        "seed": SEED,
        "rng_algorithm": "numpy.PCG64",
        "uncertainty_scope": "territorial vote composition; not a seat forecast",
        "external_audit": False,
        "parties": {
            p: {
                "observed_share": float(observed[p]),
                "p10": float(np.quantile(arr, 0.10)),
                "p50": float(np.quantile(arr, 0.50)),
                "p90": float(np.quantile(arr, 0.90)),
            }
            for p, arr in sorted(party_draws.items())
        },
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
