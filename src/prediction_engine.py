"""Prediction-first engine: historical party swings + turnout + exact electoral allocation.

No electoral observations are embedded here. The engine only transforms supplied,
versioned data and records every assumption explicitly.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from fractions import Fraction
from typing import Mapping, Sequence
from .electoral import allocate

@dataclass(frozen=True)
class PartySwing:
    party: str
    share_change: float
    basis: str
    observations: int

@dataclass(frozen=True)
class PredictionScenario:
    name: str
    turnout: float
    swing_method: str
    assumptions: tuple[str, ...] = ()

def _shares(votes: Mapping[str, int]) -> dict[str, float]:
    total = sum(votes.values())
    if total <= 0:
        raise ValueError("La circunscripción no tiene votos")
    return {p: v / total for p, v in votes.items()}

def historical_share_changes(
    historical: Sequence[Mapping[str, Mapping[str, int]]],
    current: Mapping[str, Mapping[str, int]],
) -> dict[str, dict[str, float]]:
    """Median party share change by constituency across supplied historical elections.

    Historical observations must be chronologically ordered and comparable.
    Missing parties are treated as zero only when explicitly present as a
    zero-vote party in the current/historical schema; otherwise the party is
    excluded from that observation.
    """
    if not historical:
        raise ValueError("Se necesita al menos una elección histórica")
    out: dict[str, dict[str, float]] = {}
    for constituency, current_row in current.items():
        observations: dict[str, list[float]] = {p: [] for p in current_row}
        for election in historical:
            if constituency not in election:
                continue
            old = election[constituency]
            old_total = sum(old.values())
            new_total = sum(current_row.values())
            if old_total <= 0 or new_total <= 0:
                continue
            old_shares = _shares(old)
            for p in observations:
                if p in old_shares:
                    observations[p].append(_shares(current_row)[p] - old_shares[p])
        out[constituency] = {
            p: _median(xs) if xs else 0.0
            for p, xs in observations.items()
        }
    return out

def _median(values: Sequence[float]) -> float:
    xs = sorted(values)
    if not xs:
        return 0.0
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2

def apply_share_swing(
    votes_by_constituency: Mapping[str, Mapping[str, int]],
    share_changes: Mapping[str, Mapping[str, float]],
    turnout_targets: Mapping[str, float] | None = None,
) -> dict[str, dict[str, int]]:
    """Apply explicit share changes and optional turnout targets with largest-remainder rounding.

    Share changes are additive to current vote shares. Negative votes or shares
    outside [0,1] are rejected. Turnout is represented by a multiplicative
    valid-vote target relative to the supplied baseline, so no population data
    are invented.
    """
    out: dict[str, dict[str, int]] = {}
    turnout_targets = turnout_targets or {}
    for c, row in votes_by_constituency.items():
        base_total = sum(row.values())
        if base_total <= 0:
            raise ValueError(f"{c}: votos base inválidos")
        changes = share_changes.get(c, {})
        raw_shares = {p: row[p] / base_total + changes.get(p, 0.0) for p in row}
        if any(v < -1e-12 or v > 1 + 1e-12 for v in raw_shares.values()):
            raise ValueError(f"{c}: cuota prevista fuera de [0,1]")
        share_total = sum(raw_shares.values())
        if share_total <= 0:
            raise ValueError(f"{c}: cuotas previstas inválidas")
        raw_shares = {p: max(0.0, v / share_total) for p, v in raw_shares.items()}
        target_total = base_total * float(turnout_targets.get(c, 1.0))
        if target_total < 0:
            raise ValueError(f"{c}: participación objetivo inválida")
        raw = {p: raw_shares[p] * target_total for p in row}
        floors = {p: int(v) for p, v in raw.items()}
        remainder = int(round(target_total)) - sum(floors.values())
        order = sorted(raw, key=lambda p: (raw[p] - floors[p], p), reverse=True)
        for p in order[:max(0, remainder)]:
            floors[p] += 1
        out[c] = floors
    return out

def scenario_catalog(turnout_scenarios: Sequence[tuple[str, float]]) -> list[dict]:
    if not turnout_scenarios:
        raise ValueError("Faltan escenarios de participación")
    return [asdict(PredictionScenario(
        name=name, turnout=float(turnout), swing_method="historical_median_share_change",
        assumptions=("participación suministrada por el usuario/modelo histórico",
                     "cambio de cuota mediano por circunscripción",
                     "D'Hondt exacto; sin transferencia inventada"),
    )) for name, turnout in turnout_scenarios]

def predict(
    votes_by_constituency: Mapping[str, Mapping[str, int]],
    seats_by_constituency: Mapping[str, int],
    blank_votes_by_constituency: Mapping[str, int],
    share_changes: Mapping[str, Mapping[str, float]],
    turnout_factors: Mapping[str, float] | None = None,
    special_by_constituency: Mapping[str, str] | None = None,
) -> dict:
    special_by_constituency = special_by_constituency or {}
    adjusted = apply_share_swing(votes_by_constituency, share_changes, turnout_factors)
    national: dict[str, int] = {}
    by_constituency: dict[str, dict[str, int]] = {}
    for c, row in adjusted.items():
        valid = sum(row.values()) + blank_votes_by_constituency[c]
        result = allocate(row, seats_by_constituency[c], valid,
                          special_by_constituency.get(c, ""), blank_votes_by_constituency[c])
        if result.status != "OK":
            raise RuntimeError(f"{c}: {result.status}")
        by_constituency[c] = result.seats
        for p, s in result.seats.items():
            national[p] = national.get(p, 0) + s
    if sum(national.values()) != sum(seats_by_constituency.values()):
        raise AssertionError("Los escaños previstos no suman la magnitud electoral")
    return {"votes": adjusted, "seats_by_constituency": by_constituency,
            "national_seats": national}
