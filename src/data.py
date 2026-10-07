"""Única frontera de datos del dominio electoral.

Normaliza y valida observaciones; no contiene predicción, D'Hondt ni decisión.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import Iterable, Mapping, Sequence

@dataclass(frozen=True)
class PollObservation:
    election: str
    election_date: str
    party: str
    poll: float
    actual: float
    house: str
    field_end: str
    source: str
    poll_id: str = ""
    governing_party: str = ""
    government_status: str = ""
    government_change: str = ""
    party_family: str = ""
    poll_method: str = ""
    sample_size: int | None = None
    source_tier: str = ""

    @property
    def error(self) -> float:
        return self.poll - self.actual

    @property
    def abs_error(self) -> float:
        return abs(self.error)

    @property
    def error_direction(self) -> str:
        if self.error > 0: return "SOBREESTIMACION"
        if self.error < 0: return "SUBESTIMACION"
        return "CERO"

    @property
    def change_magnitude(self) -> float:
        return abs(self.error)

    @property
    def days_to_election(self) -> int:
        return (date.fromisoformat(self.election_date) -
                date.fromisoformat(self.field_end)).days

def validate_votes(votes: Mapping[str, int]) -> None:
    if not isinstance(votes, Mapping):
        raise TypeError("votes debe ser un mapping")
    if any(not isinstance(p, str) or not p.strip() for p in votes):
        raise ValueError("nombres inválidos")
    if any(isinstance(v, bool) or not isinstance(v, int) or v < 0 for v in votes.values()):
        raise ValueError("votos inválidos")

def merge_votes(*matrices: Mapping[str, int]) -> dict[str, int]:
    out: dict[str, int] = {}
    for matrix in matrices:
        validate_votes(matrix)
        for party, votes in matrix.items():
            out[party] = out.get(party, 0) + votes
    return out

def validate_share_vector(shares: Mapping[str, float], tolerance: float = 1e-9) -> None:
    if not shares or any(float(v) < 0 for v in shares.values()):
        raise ValueError("proporciones inválidas")
    if abs(sum(float(v) for v in shares.values()) - 1.0) > tolerance:
        raise ValueError("las proporciones deben sumar 1")

def validate_constituency_matrix(
    votes_by_constituency: Mapping[str, Mapping[str, int]],
    seats_by_constituency: Mapping[str, int],
) -> None:
    if set(votes_by_constituency) != set(seats_by_constituency):
        raise ValueError("claves de circunscripción no coinciden")
    for votes in votes_by_constituency.values():
        validate_votes(votes)
    if any(isinstance(s, bool) or not isinstance(s, int) or s < 1
           for s in seats_by_constituency.values()):
        raise ValueError("escaños inválidos")
