"""Canonical real-estimation pipeline.

Consumes only materialized observations. National polling never becomes
territorial seats by inference. A seat result requires an explicit 52-
constituency vote matrix and validated legal magnitudes.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .coalition import CoalitionDecisionEngine, CoalitionScenario
from .electoral import allocate
from .electoral_radar_adapter import build_radar_from_snapshot
from .marginality import rank_marginality

EXPECTED_CONSTITUENCIES = 52
EXPECTED_SEATS = 350


class PipelineBlocked(RuntimeError):
    pass


def _hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def validate_territorial_matrix(
    votes: Mapping[str, Mapping[str, int]],
    seats: Mapping[str, int],
    blank: Mapping[str, int],
    special: Mapping[str, str],
) -> None:
    if len(votes) != EXPECTED_CONSTITUENCIES:
        raise PipelineBlocked(f"BLOCKED_TERRITORY_COUNT:{len(votes)}")
    if set(votes) != set(seats) or set(votes) != set(blank):
        raise PipelineBlocked("BLOCKED_TERRITORY_KEYS")
    if sum(seats.values()) != EXPECTED_SEATS:
        raise PipelineBlocked("BLOCKED_SEAT_MAGNITUDE")
    for c, row in votes.items():
        if not row or any(type(v) is not int or v < 0 for v in row.values()):
            raise PipelineBlocked(f"BLOCKED_INVALID_VOTES:{c}")
        if type(blank[c]) is not int or blank[c] < 0:
            raise PipelineBlocked(f"BLOCKED_INVALID_BLANK:{c}")
        valid = sum(row.values()) + blank[c]
        result = allocate(row, seats[c], valid, special.get(c, ""), blank[c])
        if result.status != "OK":
            raise PipelineBlocked(f"BLOCKED_ELECTORAL_ALLOCATION:{c}:{result.status}")


def materialize_observations(
    validated_polls: Sequence[Mapping[str, Any]],
    output: Path,
) -> dict[str, Any]:
    polls = [dict(p) for p in validated_polls]
    if not polls:
        raise PipelineBlocked("BLOCKED_NO_OBSERVED_POLLS")
    territorial = [p for p in polls if p.get("territorial")]
    payload = {
        "schema": "REAL_ESTIMATION_OBSERVATIONS_V1",
        "status": "READY" if territorial else "BLOCKED_NO_TERRITORIAL_OBSERVATION",
        "national_poll_count": len(polls),
        "territorial_poll_count": len(territorial),
        "polls": polls,
        "policy": {
            "observed_only": True,
            "national_to_territorial_inference": False,
            "unverified_values": False,
        },
        "input_hash": _hash(polls),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def run_real_estimation(
    *,
    observations: Mapping[str, Any],
    votes: Mapping[str, Mapping[str, int]] | None,
    seats: Mapping[str, int] | None,
    blank: Mapping[str, int] | None,
    special: Mapping[str, str] | None = None,
    coalition_parties: Sequence[str] = (),
    previous_snapshot: Mapping[str, Any] | None = None,
    today,
    iterations: int = 10000,
    seed: int = 20261006,
) -> dict[str, Any]:
    if observations.get("status") != "READY":
        raise PipelineBlocked(str(observations.get("status", "BLOCKED_OBSERVATIONS")))
    if votes is None or seats is None or blank is None:
        raise PipelineBlocked("BLOCKED_NO_TERRITORIAL_INPUT")
    special = dict(special or {})
    validate_territorial_matrix(votes, seats, blank, special)

    from .projection_suite import project
    from .uncertainty import SimulationConfig, run_monte_carlo

    base = project(votes, seats, blank, {}, {}, special)
    marginal = rank_marginality([
        {"name": c, "votes": votes[c], "seats": seats[c],
         "blank_votes": blank[c], "special": special.get(c, "")}
        for c in votes
    ])

    coalitions = None
    if coalition_parties:
        engine = CoalitionDecisionEngine(seats, blank, special)
        scenario = CoalitionScenario(
            "observed_territorial",
            votes,
            assumptions=("observed territorial input", "no vote transfer inference"),
            source="materialized_observation",
        )
        coalitions = engine.analyze_coalition(tuple(coalition_parties), [scenario])

    # Uncertainty is deliberately unavailable unless the input contains an
    # explicit territorial sampler. Never invent a covariance structure here.
    uncertainty = None
    if "territorial_draws" in observations:
        draws = observations["territorial_draws"]
        if not isinstance(draws, list) or len(draws) < iterations:
            raise PipelineBlocked("BLOCKED_INSUFFICIENT_TERRITORIAL_DRAWS")
        index = {"i": 0}

        def sampler(_rng):
            row = draws[index["i"]]
            index["i"] += 1
            return row

        uncertainty = run_monte_carlo(
            sampler, seats, blank, special,
            SimulationConfig(iterations=iterations, seed=seed),
        )
    snapshot = {
        "status": "EXECUTED_REAL_ESTIMATION",
        "territory": "EXPLICIT_52_CONSTITUENCIES",
        "projection": base,
        "marginality": {"most_marginal": marginal[:20]},
        "coalitions": coalitions,
        "uncertainty": uncertainty,
        "traceability": {
            "input_hash": _hash({"observations": observations, "votes": votes}),
            "output_hash": _hash({"projection": base, "marginality": marginal, "coalitions": coalitions, "uncertainty": uncertainty}),
        },
    }
    radar = build_radar_from_snapshot(
        today=today,
        current=snapshot,
        previous=previous_snapshot,
        evidence_refs=[observations.get("input_hash", "")],
    )
    return {"snapshot": snapshot, "radar": radar}


__all__ = ["PipelineBlocked", "materialize_observations", "run_real_estimation", "validate_territorial_matrix"]
