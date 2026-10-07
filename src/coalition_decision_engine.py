"""Decision Engine de coaliciones: beneficio, robustez y riesgo."""
from __future__ import annotations
from dataclasses import dataclass, asdict
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

class CoalitionDecisionEngine:
    """Compara candidaturas separadas frente a coalición por circunscripción.

    Los escenarios son datos explícitos: el motor no inventa shifts de voto.
    """

    def __init__(self, seats_by_constituency, blank_votes_by_constituency=None,
                 special_by_constituency=None):
        self.seats = dict(seats_by_constituency)
        self.blank = dict(blank_votes_by_constituency or {})
        self.special = dict(special_by_constituency or {})
        if not self.seats or any(
            isinstance(n, bool) or not isinstance(n, int) or n < 1
            for n in self.seats.values()
        ):
            raise ValueError("Magnitud electoral inválida")

    @staticmethod
    def generate_all_coalitions(parties: Sequence[str], min_size=2,
                                max_size=None, max_combinations=100000):
        unique = tuple(dict.fromkeys(p for p in parties if p))
        if min_size < 2 or min_size > len(unique):
            raise ValueError("Tamaño mínimo de coalición inválido")
        max_size = len(unique) if max_size is None else min(max_size, len(unique))
        count = sum(comb(len(unique), k) for k in range(min_size, max_size + 1))
        if count > max_combinations:
            raise ValueError(f"ESPACIO_EXCESIVO: {count} coaliciones; "
                             "defina max_size o aumente max_combinations explícitamente")
        return [c for k in range(min_size, max_size + 1)
                for c in combinations(unique, k)]

    def _validate(self, scenario):
        if set(scenario.votes) != set(self.seats):
            raise ValueError(f"{scenario.name}: circunscripciones incompatibles")
        for c, row in scenario.votes.items():
            if any(isinstance(v, bool) or not isinstance(v, int) or v < 0 for v in row.values()):
                raise ValueError(f"{scenario.name}/{c}: votos inválidos")
            if sum(row.values()) + self.blank.get(c, 0) <= 0:
                raise ValueError(f"{scenario.name}/{c}: votos válidos inválidos")

    def _allocate(self, row, c):
        valid = sum(row.values()) + self.blank.get(c, 0)
        a = allocate(row, self.seats[c], valid, self.special.get(c, ""),
                     self.blank.get(c, 0))
        if a.status != "OK":
            raise RuntimeError(f"BLOCKED:{c}:{a.status}")
        return a

    def _outcome(self, scenario, parties):
        name = "+".join(parties)
        separate = coalition = 0
        for c, row in scenario.votes.items():
            if any(p not in row for p in parties):
                raise ValueError(f"{scenario.name}/{c}: candidatura ausente")
            a = self._allocate(row, c)
            separate += sum(a.seats.get(p, 0) for p in parties)
            merged = dict(row)
            merged[name] = sum(row[p] for p in parties)
            for p in parties:
                del merged[p]
            b = self._allocate(merged, c)
            coalition += b.seats.get(name, 0)
        return ScenarioOutcome(scenario.name, scenario.weight, separate, coalition,
                               coalition - separate)

    def _threshold_waste(self, scenario, parties, merged):
        total = 0
        name = "+".join(parties)
        for c, row in scenario.votes.items():
            valid = sum(row.values()) + self.blank.get(c, 0)
            if merged:
                v = sum(row[p] for p in parties)
                total += v if v * 100 < valid * 3 else 0
            else:
                total += sum(v for p, v in row.items()
                             if p in parties and v * 100 < valid * 3)
        return total

    def _impacts(self, scenario, parties):
        name = "+".join(parties)
        out = []
        for c, row in scenario.votes.items():
            a = self._allocate(row, c)
            merged = dict(row)
            merged[name] = sum(row[p] for p in parties)
            for p in parties:
                del merged[p]
            b = self._allocate(merged, c)
            s = sum(a.seats.get(p, 0) for p in parties)
            j = b.seats.get(name, 0)
            if s != j:
                out.append({"constituency": c, "separate": s,
                            "coalition": j, "delta": j - s})
        return sorted(out, key=lambda x: (-abs(x["delta"]), x["constituency"]))

    def analyze_coalition(self, parties, scenarios):
        parties = tuple(dict.fromkeys(parties))
        if len(parties) < 2 or not scenarios:
            raise ValueError("Se necesitan al menos dos candidaturas y un escenario")
        for s in scenarios:
            self._validate(s)
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
        risk = "LOW" if p_nonpositive == 0 and min(deltas) > 0 else (
            "MEDIUM" if p_nonpositive <= 1/3 else "HIGH")
        robustness = ("HIGH" if min(deltas) > 0 and p_positive >= .95 else
                      "MEDIUM" if p_positive >= 2/3 else "LOW")
        return {
            "coalition": list(parties),
            "separate_seats": outcomes[0].separate_seats,
            "coalition_seats": outcomes[0].coalition_seats,
            "benefit": outcomes[0].delta,
            "price": {
                "vote_contribution": {p: sum(central.votes[c].get(p, 0)
                                             for c in central.votes) for p in parties},
                "threshold_wasted_votes_separate": waste_sep,
                "threshold_wasted_votes_coalition": waste_coal,
                "threshold_votes_recovered": waste_sep - waste_coal,
            },
            "scenarios": [asdict(o) for o in outcomes],
            "robustness": {
                "level": robustness, "worst_case_delta": min(deltas),
                "best_case_delta": max(deltas), "weighted_mean_delta": mean,
                "weighted_improvement": p_positive,
                "weighted_non_improvement": p_nonpositive,
                "weighted_std_delta": sqrt(variance),
            },
            "risk": {"level": risk, "weighted_non_improvement": p_nonpositive, "weight_interpretation": "Los pesos son pesos relativos de escenarios; no son una probabilidad calibrada."},
            "decisive_constituencies": self._impacts(central, parties),
        }

    def analyze_all_coalitions(self, parties, scenarios, min_size=2,
                               max_size=None, max_combinations=100000):
        coalitions = self.generate_all_coalitions(parties, min_size, max_size,
                                                   max_combinations)
        results = [self.analyze_coalition(c, scenarios) for c in coalitions]
        results.sort(key=lambda r: (r["robustness"]["weighted_mean_delta"],
                                    r["robustness"]["weighted_improvement"],
                                    r["robustness"]["worst_case_delta"],
                                    r["benefit"]), reverse=True)
        return {
            "coalition_count": len(results),
            "all_coalitions": results,
            "ranking": [
                {
                    "coalition": r["coalition"],
                    "separate": r["separate_seats"],
                    "coalition_seats": r["coalition_seats"],
                    "difference": r["benefit"],
                    "risk": r["risk"]["level"],
                    "weighted_mean_difference": r["robustness"]["weighted_mean_delta"],
                    "worst_case_difference": r["robustness"]["worst_case_delta"],
                }
                for r in results
            ],
        }
