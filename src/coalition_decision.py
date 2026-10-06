"""Decision-facing coalition analysis.

Answers: what changes if parties run together, where, and by how many seats?
It never adds published seat totals; it recomputes D'Hondt from constituency votes.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Mapping, Sequence
from .electoral import allocate

@dataclass(frozen=True)
class ConstituencyImpact:
    constituency: str
    separate_seats: int
    coalition_seats: int
    delta: int

def coalition_decision(
    votes_by_constituency: Mapping[str, Mapping[str, int]],
    seats_by_constituency: Mapping[str, int],
    blank_votes_by_constituency: Mapping[str, int],
    coalition: Sequence[str],
    special_by_constituency: Mapping[str, str] | None = None,
) -> dict:
    parties=tuple(coalition)
    if len(parties)<2 or len(set(parties))!=len(parties):
        raise ValueError("La coalición requiere al menos dos candidaturas distintas")
    special_by_constituency=special_by_constituency or {}
    name="+".join(parties)
    impacts=[]
    baseline_national={}
    coalition_national={}
    for c,row in votes_by_constituency.items():
        if any(p not in row for p in parties):
            raise ValueError(f"{c}: falta una candidatura de la coalición")
        valid=sum(row.values())+blank_votes_by_constituency[c]
        base=allocate(row,seats_by_constituency[c],valid,special_by_constituency.get(c,""),blank_votes_by_constituency[c])
        merged=dict(row)
        merged[name]=sum(row[p] for p in parties)
        for p in parties: del merged[p]
        joined=allocate(merged,seats_by_constituency[c],valid,special_by_constituency.get(c,""),blank_votes_by_constituency[c])
        if base.status!="OK" or joined.status!="OK":
            raise RuntimeError(f"{c}: asignación bloqueada")
        separate=sum(base.seats.get(p,0) for p in parties)
        together=joined.seats.get(name,0)
        impacts.append(ConstituencyImpact(c,separate,together,together-separate))
        for p,s in base.seats.items(): baseline_national[p]=baseline_national.get(p,0)+s
        for p,s in joined.seats.items(): coalition_national[p]=coalition_national.get(p,0)+s
    changed=sorted((asdict(x) for x in impacts if x.delta), key=lambda x:(-abs(x["delta"]),x["constituency"]))
    return {
        "coalition":name,
        "baseline_seats":baseline_national,
        "coalition_seats":coalition_national,
        "total_separate":sum(baseline_national.get(p,0) for p in parties),
        "total_coalition":coalition_national.get(name,0),
        "delta":coalition_national.get(name,0)-sum(baseline_national.get(p,0) for p in parties),
        "affected_constituencies":changed,
        "all_constituencies":[asdict(x) for x in impacts],
        "interpretation":"positive delta = seats gained by running together; negative delta = seats lost",
    }
