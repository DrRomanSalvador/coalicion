"""Motor electoral determinista para Congreso de los Diputados."""
from fractions import Fraction
from dataclasses import dataclass
from typing import Dict, Tuple

@dataclass(frozen=True)
class Allocation:
    seats: Dict[str, int]
    status: str
    tie: Tuple[str, ...] = ()

def dhondt(votes: Dict[str, int], seats: int, valid_votes: int) -> Allocation:
    if seats < 1:
        raise ValueError("seats debe ser >= 1")
    if valid_votes < 0:
        raise ValueError("valid_votes no puede ser negativo")
    eligible = {p: v for p, v in votes.items() if Fraction(v * 100, valid_votes or 1) >= 3}
    quotients = [(Fraction(v, d), v, p, d) for p, v in eligible.items() for d in range(1, seats + 1)]
    quotients.sort(key=lambda x: (x[0], x[1]), reverse=True)
    selected = quotients[:seats]
    if len(selected) < seats:
        return Allocation({p: 0 for p in votes}, "INSUFICIENTES_CANDIDATURAS")
    boundary = selected[-1]
    same_q = [q for q in quotients if q[0] == boundary[0]]
    if len(same_q) > sum(q[0] == boundary[0] for q in selected):
        same_votes = [q for q in same_q if q[1] == boundary[1]]
        if same_votes:
            return Allocation({p: 0 for p in votes}, "EMPATE_ABSOLUTO_PENDIENTE",
                               tuple(sorted(q[2] for q in same_votes)))
    out = {p: 0 for p in votes}
    for _, _, p, _ in selected:
        out[p] += 1
    return Allocation(out, "OK")

def ceuta_melilla(votes: Dict[str, int]) -> Allocation:
    if not votes:
        raise ValueError("Se requiere al menos una candidatura")
    maximum = max(votes.values())
    winners = tuple(sorted(p for p, v in votes.items() if v == maximum))
    if len(winners) > 1:
        return Allocation({p: 0 for p in votes}, "EMPATE_MAYORIA_PENDIENTE", winners)
    return Allocation({p: int(p == winners[0]) for p in votes}, "OK")

def allocate(votes: Dict[str, int], seats: int, valid_votes: int, special: str = "") -> Allocation:
    if special in {"Ceuta", "Melilla"}:
        if seats != 1:
            raise ValueError("Ceuta/Melilla deben tener exactamente 1 diputado")
        return ceuta_melilla(votes)
    return dhondt(votes, seats, valid_votes)

def merge_candidacies(*matrices: Dict[str, int]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for matrix in matrices:
        for party, votes in matrix.items():
            out[party] = out.get(party, 0) + votes
    return out
