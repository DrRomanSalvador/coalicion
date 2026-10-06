"""Motor de escenarios de predicción electoral; no sustituye el resultado observado."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from fractions import Fraction
from statistics import mean
from typing import Mapping
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
