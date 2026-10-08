"""Neutral, descriptive coalition enumeration for constituency-level Congress results."""
from __future__ import annotations
from dataclasses import dataclass
from itertools import combinations
from typing import Mapping, Sequence
from .electoral import allocate

@dataclass(frozen=True)
class CoalitionResult:
    coalition: tuple[str, ...]
    separate_seats: int
    coalition_seats: int
    delta: int
    separate_by_constituency: dict[str, int]
    coalition_by_constituency: dict[str, int]
    delta_by_constituency: dict[str, int]

def _parties(parties: Sequence[str]) -> tuple[str, ...]:
    out=tuple(sorted({str(p).strip() for p in parties if str(p).strip()}))
    if len(out)<2: raise ValueError("se requieren al menos dos candidaturas")
    return out

def calculate_coalition(votes_by_constituency: Mapping[str, Mapping[str,int]],
                        seats_by_constituency: Mapping[str,int],
                        valid_votes: Mapping[str,int], coalition: Sequence[str],
                        special=None, blank=None) -> CoalitionResult:
    members=_parties(coalition); special=special or {}; blank=blank or {}
    if set(votes_by_constituency)!=set(seats_by_constituency) or set(votes_by_constituency)!=set(valid_votes):
        raise ValueError("las claves de circunscripción deben coincidir")
    separate_by={}; coalition_by={}
    for c,row0 in votes_by_constituency.items():
        row=dict(row0)
        for p in members:
            row.setdefault(p, 0)
        a=allocate(row,seats_by_constituency[c],valid_votes[c],special.get(c,""),blank.get(c,0))
        if a.status!="OK": raise RuntimeError(f"BLOCKED:{c}:{a.status}")
        name=" + ".join(members)
        merged={p:v for p,v in row.items() if p not in members}
        merged[name]=sum(row.get(p, 0) for p in members)
        b=allocate(merged,seats_by_constituency[c],valid_votes[c],special.get(c,""),blank.get(c,0))
        if b.status!="OK": raise RuntimeError(f"BLOCKED:{c}:{b.status}")
        separate_by[c]=sum(a.seats.get(p,0) for p in members)
        coalition_by[c]=b.seats.get(name,0)
    delta_by={c:coalition_by[c]-separate_by[c] for c in separate_by}
    return CoalitionResult(members,sum(separate_by.values()),sum(coalition_by.values()),
                           sum(delta_by.values()),separate_by,coalition_by,delta_by)

def enumerate_coalitions(parties: Sequence[str], min_size=2, max_size=None):
    universe=tuple(sorted({str(p).strip() for p in parties if str(p).strip()}))
    if len(universe)<2: raise ValueError("se requieren al menos dos candidaturas")
    max_size=len(universe) if max_size is None else max_size
    if not 2<=min_size<=max_size<=len(universe): raise ValueError("tamaños de coalición inválidos")
    for size in range(min_size,max_size+1): yield from combinations(universe,size)

def enumerate_all_coalition_results(votes_by_constituency,seats_by_constituency,valid_votes,
                                    parties,special=None,blank=None,min_size=2,max_size=None):
    for coalition in enumerate_coalitions(parties,min_size,max_size):
        yield calculate_coalition(votes_by_constituency,seats_by_constituency,valid_votes,
                                  coalition,special,blank)
