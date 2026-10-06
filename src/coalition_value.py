"""Valor marginal de una coalición bajo la ley electoral española.

No suma escaños de partidos. Fusiona votos por circunscripción y vuelve a ejecutar
el motor electoral. La comparación es, por construcción, falsable y reproducible.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping
from .electoral import allocate


@dataclass(frozen=True)
class CoalitionDelta:
    constituency: str
    separate_seats: int
    coalition_seats: int
    delta: int


def coalition_delta(
    constituencies: Mapping[str, Mapping[str, int]],
    seats: Mapping[str, int],
    coalition: tuple[str, ...],
    valid_votes: Mapping[str, int],
) -> list[CoalitionDelta]:
    if len(coalition) < 2:
        raise ValueError("Una coalición requiere al menos dos candidaturas")
    if set(coalition) != set(dict.fromkeys(coalition)):
        raise ValueError("Candidaturas duplicadas en la coalición")

    out = []
    for c, votes in constituencies.items():
        s = seats[c]
        vv = valid_votes[c]

        for p in coalition:
            if p not in votes:
                raise ValueError(f"Falta {p} en {c}")
        separate_result = allocate(dict(votes), s, vv)
        separate = sum(separate_result.seats[p] for p in coalition)

        merged = dict(votes)
        merged_name = "+".join(coalition)
        merged[merged_name] = sum(votes[p] for p in coalition)
        for p in coalition:
            del merged[p]

        result = allocate(merged, s, vv)
        coalition_seats = result.seats[merged_name]
        out.append(CoalitionDelta(c, separate, coalition_seats, coalition_seats - separate))
    return out
