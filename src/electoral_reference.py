"""Independent reference allocator for differential testing.

This intentionally uses a quotient table rather than the production allocator's
per-round quotient mapping. It is a verification oracle, not a second product API.
"""
from __future__ import annotations
from fractions import Fraction
from typing import Mapping


def allocate_reference(votes: Mapping[str, int], seats: int, valid_votes_total: int,
                       blank_votes: int = 0, threshold: Fraction = Fraction(3, 100),
                       special: str = "") -> dict[str, int]:
    if not isinstance(seats, int) or isinstance(seats, bool) or seats < 1:
        raise ValueError("seats inválido")
    if not isinstance(valid_votes_total, int) or isinstance(valid_votes_total, bool) or valid_votes_total <= 0:
        raise ValueError("valid_votes inválido")
    if not isinstance(blank_votes, int) or isinstance(blank_votes, bool) or blank_votes < 0:
        raise ValueError("blank_votes inválido")
    if any(not isinstance(p, str) or not p.strip() for p in votes):
        raise ValueError("nombres inválidos")
    if any(isinstance(v, bool) or not isinstance(v, int) or v < 0 for v in votes.values()):
        raise ValueError("votos inválidos")
    if sum(votes.values()) + blank_votes != valid_votes_total:
        raise ValueError("candidaturas + blancos debe coincidir con votos válidos")
    if special in {"Ceuta", "Melilla"}:
        if seats != 1:
            raise ValueError("Ceuta/Melilla: 1 escaño")
        top=max(votes.values())
        winners=[p for p,v in votes.items() if v==top]
        if len(winners)!=1:
            raise RuntimeError("EMPATE_MAYORIA_PENDIENTE")
        return {p:int(p==winners[0]) for p in votes}
    eligible={p:v for p,v in votes.items() if Fraction(v,valid_votes_total)>=threshold}
    result={p:0 for p in votes}
    for _ in range(seats):
        quotients=[]
        for p,v in eligible.items():
            quotients.append((Fraction(v,result[p]+1), v, p))
        if not quotients:
            raise RuntimeError("INSUFICIENTES_CANDIDATURAS")
        top=max(q for q,_,_ in quotients)
        tied=[(v,p) for q,v,p in quotients if q==top]
        maxv=max(v for v,_ in tied)
        tied=[p for v,p in tied if v==maxv]
        if len(tied)!=1:
            raise RuntimeError("EMPATE_ABSOLUTO_PENDIENTE")
        result[tied[0]] += 1
    return result
