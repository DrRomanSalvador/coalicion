"""Escenarios contrafactuales neutrales: separados, parejas y trío."""
from __future__ import annotations
from typing import Mapping
from .electoral import allocate
def merge_scenario(votes_by_constituency:Mapping[str,Mapping[str,int]],coalition:tuple[str,...]):
    if len(coalition)<2 or len(set(coalition))!=len(coalition): raise ValueError("coalición inválida")
    out={}; name="+".join(coalition)
    for c,votes in votes_by_constituency.items():
        if any(p not in votes for p in coalition): raise ValueError(f"candidatura ausente en {c}")
        row=dict(votes); row[name]=sum(row[p] for p in coalition)
        for p in coalition: del row[p]
        out[c]=row
    return out
def compare_scenarios(votes_by_constituency,seats_by_constituency,valid_votes,blank_votes,coalitions,special_by_constituency=None):
    special_by_constituency = special_by_constituency or {}
    scenarios={"SEPARADOS":dict(votes_by_constituency)}
    for co in coalitions: scenarios["+".join(co)]=merge_scenario(votes_by_constituency,co)
    out={}
    for name,rows in scenarios.items():
        nat={}
        for c,votes in rows.items():
            r=allocate(votes,seats_by_constituency[c],valid_votes[c],special_by_constituency.get(c,""),blank_votes[c])
            if r.status!="OK": raise RuntimeError(f"escenario bloqueado: {c}: {r.status}")
            for p,s in r.seats.items(): nat[p]=nat.get(p,0)+s
        if sum(nat.values())!=sum(seats_by_constituency.values()): raise AssertionError("escaños no conservados")
        out[name]=nat
    return out
