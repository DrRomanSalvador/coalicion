"""Canonical prediction layer: explicit historical transformations and electoral scenarios."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from fractions import Fraction
from typing import Mapping, Sequence
from .electoral import allocate

@dataclass(frozen=True)
class TurnoutScenario:
    name: str
    turnout: float
    basis: str

def historical_turnout_scenarios(turnouts: list[float], window: int = 5) -> list[TurnoutScenario]:
    vals = [float(x) for x in turnouts if 0 < float(x) < 1]
    if not vals:
        raise ValueError("Se necesitan participaciones históricas")
    vals = vals[-window:]
    ordered = sorted(vals)
    n = len(ordered)
    q25 = ordered[int((n - 1) * 0.25)]
    q50 = ordered[int((n - 1) * 0.50)]
    q75 = ordered[int((n - 1) * 0.75)]
    return [
        TurnoutScenario("baja", q25, f"percentil_25_últimos_{len(vals)}"),
        TurnoutScenario("central", q50, f"mediana_últimos_{len(vals)}"),
        TurnoutScenario("alta", q75, f"percentil_75_últimos_{len(vals)}"),
    ]

def rescale_votes_by_turnout(votes: Mapping[str, int], observed_turnout: float, target_turnout: float) -> dict[str, int]:
    if not 0 < observed_turnout <= 1 or not 0 < target_turnout <= 1:
        raise ValueError("participación fuera de rango")
    factor = Fraction(str(target_turnout)) / Fraction(str(observed_turnout))
    return {p: max(0, int(round(v * float(factor)))) for p, v in votes.items()}

def simulate_constituency(votes: Mapping[str, int], seats: int, blank: int, target_turnout_factor: float = 1.0) -> dict:
    adjusted = {p: max(0, int(round(v * target_turnout_factor))) for p, v in votes.items()}
    valid = sum(adjusted.values()) + blank
    result = allocate(adjusted, seats, valid, blank_votes=blank)
    if result.status != "OK":
        raise RuntimeError(result.status)
    return {"votes": adjusted, "seats": result.seats}

def build_scenario_catalog(historical_turnouts: list[float]) -> list[dict]:
    return [asdict(x) for x in historical_turnout_scenarios(historical_turnouts)]


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
        if any(not isinstance(v, (int, float)) or not float("-inf") < float(v) < float("inf")
               for v in changes.values()):
            raise ValueError(f"{c}: cambio de cuota no finito")
        change_sum = sum(float(changes.get(p, 0.0)) for p in row)
        if abs(change_sum) > 1e-12:
            raise ValueError(f"{c}: los cambios de cuota deben sumar cero")
        raw_shares = {p: row[p] / base_total + float(changes.get(p, 0.0)) for p in row}
        if any(v < -1e-12 or v > 1 + 1e-12 for v in raw_shares.values()):
            raise ValueError(f"{c}: cuota prevista fuera de [0,1]")
        raw_shares = {p: max(0.0, v) for p, v in raw_shares.items()}
        share_total = sum(raw_shares.values())
        if abs(share_total - 1.0) > 1e-10:
            raise ValueError(f"{c}: cuotas previstas no conservan la suma unitaria")
        target_total = base_total * float(turnout_targets.get(c, 1.0))
        if target_total < 0:
            raise ValueError(f"{c}: participación objetivo inválida")
        raw = {p: raw_shares[p] * target_total for p in row}
        floors = {p: int(v) for p, v in raw.items()}
        remainder = int(round(target_total)) - sum(floors.values())
        order = sorted(raw, key=lambda p: (-(raw[p] - floors[p]), p))
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
