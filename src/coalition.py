"""Canonical coalition analysis and counterfactual engine.

All coalition calculations recompute seats from constituency votes using the
single production electoral allocator. No party-seat addition is used.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
from itertools import combinations
from math import comb, sqrt
from typing import Mapping, Sequence
from .electoral import allocate



@dataclass(frozen=True)
class CoalitionScenario:
    name: str
    votes: Mapping[str, Mapping[str, int]]
    weight: float = 1.0
    assumptions: tuple[str, ...] = ()
    source: str = "input_dataset"
    def __post_init__(self):
        if not self.name.strip() or self.weight <= 0:
            raise ValueError("Escenario inválido")

@dataclass(frozen=True)
class ScenarioOutcome:
    name: str
    weight: float
    separate_seats: int
    coalition_seats: int
    delta: int

def merge_coalition_votes(votes_by_constituency, coalition):
    """Merge selected candidacies; seat allocation remains canonical in electoral.allocate."""
    parties = tuple(dict.fromkeys(coalition))
    if len(parties) < 2:
        raise ValueError("La coalición requiere al menos dos candidaturas")
    name = "+".join(parties)
    out = {}
    for constituency, row in votes_by_constituency.items():
        merged = dict(row)
        for p in parties:
            merged.setdefault(p, 0)
        merged[name] = sum(merged.pop(p) for p in parties)
        out[constituency] = merged
    return out


def coalition_decision(
    votes_by_constituency: Mapping[str, Mapping[str, int]],
    seats_by_constituency: Mapping[str, int],
    blank_votes_by_constituency: Mapping[str, int],
    coalition: Sequence[str],
    special_by_constituency: Mapping[str, str] | None = None,
) -> dict:
    parties = tuple(coalition)
    if len(parties) < 2 or len(set(parties)) != len(parties):
        raise ValueError("La coalición requiere al menos dos candidaturas distintas")
    scenario = CoalitionScenario(
        "central",
        votes_by_constituency,
        assumptions=("coalición contrafactual", "sin transferencia de voto"),
        source="input_dataset",
    )
    return CoalitionDecisionEngine(
        seats_by_constituency,
        blank_votes_by_constituency,
        special_by_constituency,
    ).analyze_coalition(parties, [scenario])

class CoalitionDecisionEngine:
    """Compara candidaturas separadas frente a coalición por circunscripción."""

    def __init__(self, seats_by_constituency, blank_votes_by_constituency=None,
                 special_by_constituency=None):
        self.seats = dict(seats_by_constituency)
        if blank_votes_by_constituency is None:
            raise ValueError("BLOCKED: votos en blanco explícitos requeridos")
        self.blank = dict(blank_votes_by_constituency)
        self.special = dict(special_by_constituency or {})
        if not self.seats or any(
            isinstance(n, bool) or not isinstance(n, int) or n < 1
            for n in self.seats.values()
        ):
            raise ValueError("Magnitud electoral inválida")
        if set(self.blank) != set(self.seats):
            raise ValueError("BLOCKED: votos en blanco deben cubrir exactamente todas las circunscripciones")
        if set(self.special) - set(self.seats):
            raise ValueError("BLOCKED: regla especial para circunscripción inexistente")
        for special in ("Ceuta", "Melilla"):
            if special in self.seats and self.special.get(special) != special:
                raise ValueError(f"BLOCKED: falta la regla legal de {special}")
        for constituency, special in self.special.items():
            if special not in {"Ceuta", "Melilla"} or constituency != special:
                raise ValueError(f"BLOCKED: regla especial inválida para {constituency}")

    @staticmethod
    def generate_all_coalitions(parties: Sequence[str], min_size=2,
                                max_size=None, max_combinations=100000):
        unique = tuple(dict.fromkeys(p for p in parties if p))
        if min_size < 2 or min_size > len(unique):
            raise ValueError("Tamaño mínimo de coalición inválido")
        max_size = len(unique) if max_size is None else min(max_size, len(unique))
        count = sum(comb(len(unique), k) for k in range(min_size, max_size + 1))
        if count > max_combinations:
            raise ValueError(f"ESPACIO_EXCESIVO: {count} coaliciones; defina max_size o aumente max_combinations explícitamente")
        return [c for k in range(min_size, max_size + 1) for c in combinations(unique, k)]

    def _validate(self, scenario):
        if set(scenario.votes) != set(self.seats):
            raise ValueError(f"{scenario.name}: circunscripciones incompatibles")
        for c, row in scenario.votes.items():
            if any(isinstance(v, bool) or not isinstance(v, int) or v < 0 for v in row.values()):
                raise ValueError(f"{scenario.name}/{c}: votos inválidos")
            blank = self.blank[c]
            if isinstance(blank, bool) or not isinstance(blank, int) or blank < 0:
                raise ValueError(f"{scenario.name}/{c}: votos blancos inválidos")
            if sum(row.values()) + blank <= 0:
                raise ValueError(f"{scenario.name}/{c}: votos válidos inválidos")

    def _allocate(self, row, c):
        blank = self.blank[c]
        valid = sum(row.values()) + blank
        result = allocate(row, self.seats[c], valid, self.special.get(c, ""), blank)
        if result.status != "OK":
            raise RuntimeError(f"BLOCKED:{c}:{result.status}")
        return result

    def _outcome(self, scenario, parties):
        name = "+".join(parties)
        separate = coalition = 0
        for c, row in scenario.votes.items():
            row = dict(row)
            for p in parties:
                row.setdefault(p, 0)
            base = self._allocate(row, c)
            separate += sum(base.seats.get(p, 0) for p in parties)
            merged = dict(row)
            merged[name] = sum(row.get(p, 0) for p in parties)
            for p in parties:
                del merged[p]
            joined = self._allocate(merged, c)
            coalition += joined.seats.get(name, 0)
        return ScenarioOutcome(scenario.name, scenario.weight, separate, coalition, coalition - separate)

    def _threshold_waste(self, scenario, parties, merged):
        total = 0
        for c, row in scenario.votes.items():
            valid = sum(row.values()) + self.blank[c]
            votes = sum(row[p] for p in parties)
            if merged:
                total += votes if votes * 100 < valid * 3 else 0
            else:
                total += sum(row.get(p, 0) for p in parties if row.get(p, 0) * 100 < valid * 3)
        return total

    def _impacts(self, scenario, parties):
        name = "+".join(parties)
        out = []
        for c, row in scenario.votes.items():
            base = self._allocate(row, c)
            merged = dict(row)
            merged[name] = sum(row[p] for p in parties)
            for p in parties:
                del merged[p]
            joined = self._allocate(merged, c)
            separate = sum(base.seats.get(p, 0) for p in parties)
            together = joined.seats.get(name, 0)
            if separate != together:
                out.append({"constituency": c, "separate": separate, "coalition": together, "delta": together - separate})
        return sorted(out, key=lambda x: (-abs(x["delta"]), x["constituency"]))

    def _impacts_all(self, scenario, parties):
        name = "+".join(parties)
        out = []
        for c, row in scenario.votes.items():
            base = self._allocate(row, c)
            merged = dict(row)
            merged[name] = sum(row[p] for p in parties)
            for p in parties:
                del merged[p]
            joined = self._allocate(merged, c)
            separate = sum(base.seats.get(p, 0) for p in parties)
            together = joined.seats.get(name, 0)
            out.append({"constituency": c, "separate": separate, "coalition": together,
                        "delta": together - separate})
        return out

    def analyze_coalition(self, parties, scenarios):
        parties = tuple(dict.fromkeys(parties))
        if len(parties) < 2 or not scenarios:
            raise ValueError("Se necesitan al menos dos candidaturas y un escenario")
        for scenario in scenarios:
            self._validate(scenario)
        outcomes = [self._outcome(s, parties) for s in scenarios]
        weight = sum(o.weight for o in outcomes)
        mean = sum(o.weight * o.delta for o in outcomes) / weight
        p_positive = sum(o.weight for o in outcomes if o.delta > 0) / weight
        p_nonpositive = sum(o.weight for o in outcomes if o.delta <= 0) / weight
        variance = sum(o.weight * (o.delta - mean) ** 2 for o in outcomes) / weight
        deltas = [o.delta for o in outcomes]
        central = next((s for s in scenarios if s.name == "central"), None)
        if central is None:
            raise ValueError("Falta escenario explícito: central")
        waste_sep = self._threshold_waste(central, parties, False)
        waste_coal = self._threshold_waste(central, parties, True)
        return {
            "coalition": list(parties),
            "separate_seats": next(o for o in outcomes if o.name == "central").separate_seats,
            "coalition_seats": next(o for o in outcomes if o.name == "central").coalition_seats,
            "benefit": next(o for o in outcomes if o.name == "central").delta,
            "price": {
                "vote_contribution": {p: sum(central.votes[c].get(p, 0) for c in central.votes) for p in parties},
                "threshold_wasted_votes_separate": waste_sep,
                "threshold_wasted_votes_coalition": waste_coal,
                "threshold_votes_recovered": waste_sep - waste_coal,
            },
            "scenarios": [asdict(o) for o in outcomes],
            "robustness": {
                "level": ("HIGH" if min(deltas) > 0 and p_positive >= .95 else
                          "MEDIUM" if p_positive >= 2/3 else "LOW"),
                "worst_case_delta": min(deltas),
                "best_case_delta": max(deltas),
                "weighted_mean_delta": mean,
                "weighted_improvement": p_positive,
                "weighted_non_improvement": p_nonpositive,
                "weighted_std_delta": sqrt(variance),
            },
            "risk": {
                "level": ("LOW" if p_nonpositive == 0 and min(deltas) > 0 else
                          "MEDIUM" if p_nonpositive <= 1/3 else "HIGH"),
                "weighted_non_improvement": p_nonpositive,
                "weight_interpretation": "Los pesos son relativos; no son una probabilidad calibrada.",
            },
            "decisive_constituencies": self._impacts(central, parties),
            "all_constituencies": self._impacts_all(central, parties),
        }

    def analyze_all_coalitions(self, parties, scenarios, min_size=2,
                               max_size=None, max_combinations=100000):
        coalitions = self.generate_all_coalitions(parties, min_size, max_size, max_combinations)
        results = [self.analyze_coalition(c, scenarios) for c in coalitions]
        return {
            "coalition_count": len(results),
            "all_coalitions": results,
            "ranking": False,
            "policy": {
                "exhaustive_counterfactuals": True,
                "ranking_as_best_option": False,
                "recommendations": False,
            },
        }
