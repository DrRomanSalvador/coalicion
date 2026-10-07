"""Único motor de coaliciones: fusiona votos y recalcula escaños con electoral.py."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Mapping
from .electoral import allocate
from .data import merge_votes, validate_constituency_matrix

@dataclass(frozen=True)
class CoalitionDelta:
    constituency:str; separate_seats:int; coalition_seats:int; delta:int

def _validate_coalition(coalition):
    if len(coalition)<2 or len(set(coalition))!=len(coalition): raise ValueError("coalición inválida")

def merge_coalition_votes(votes_by_constituency, coalition):
    _validate_coalition(coalition); name="+".join(coalition); out={}
    for c,row in votes_by_constituency.items():
        if any(p not in row for p in coalition): raise ValueError(f"candidatura ausente en {c}")
        merged=dict(row); merged[name]=sum(row[p] for p in coalition)
        for p in coalition: del merged[p]
        out[c]=merged
    return out

def coalition_delta(constituencies,seats,coalition,valid_votes):
    _validate_coalition(coalition); out=[]
    for c,votes in constituencies.items():
        separate_result=allocate(dict(votes),seats[c],valid_votes[c])
        if separate_result.status!="OK": raise RuntimeError(separate_result.status)
        merged=merge_coalition_votes({c:votes},coalition)[c]
        merged_result=allocate(merged,seats[c],valid_votes[c])
        if merged_result.status!="OK": raise RuntimeError(merged_result.status)
        name="+".join(coalition); separate=sum(separate_result.seats[p] for p in coalition)
        joined=merged_result.seats[name]
        out.append(CoalitionDelta(c,separate,joined,joined-separate))
    return out

def compare_scenarios(votes_by_constituency,seats_by_constituency,valid_votes,blank_votes,coalitions,special_by_constituency=None):
    validate_constituency_matrix(votes_by_constituency,seats_by_constituency)
    special_by_constituency=special_by_constituency or {}
    scenarios={"SEPARADOS":dict(votes_by_constituency)}
    for coalition in coalitions: scenarios["+".join(coalition)]=merge_coalition_votes(votes_by_constituency,coalition)
    out={}
    for scenario,rows in scenarios.items():
        national={}
        for c,votes in rows.items():
            r=allocate(votes,seats_by_constituency[c],valid_votes[c],special_by_constituency.get(c,""),blank_votes[c])
            if r.status!="OK": raise RuntimeError(f"escenario bloqueado: {c}: {r.status}")
            for p,s in r.seats.items(): national[p]=national.get(p,0)+s
        if sum(national.values())!=sum(seats_by_constituency.values()): raise AssertionError("escaños no conservados")
        out[scenario]=national
    return out

def coalition_result(votes_by_constituency,seats_by_constituency,valid_votes,coalition,special=None,blank=None):
    special=special or {}; blank=blank or {}; _validate_coalition(coalition)
    separate={}; merged={}
    for c,row in votes_by_constituency.items():
        if any(p not in row for p in coalition): raise ValueError(f"{c}: candidatura ausente")
        a=allocate(row,seats_by_constituency[c],valid_votes[c],special.get(c,""),blank.get(c,0))
        m=merge_coalition_votes({c:row},coalition)[c]
        b=allocate(m,seats_by_constituency[c],valid_votes[c],special.get(c,""),blank.get(c,0))
        if a.status!="OK" or b.status!="OK": raise RuntimeError(f"BLOCKED:{c}")
        name="+".join(coalition); separate[c]=sum(a.seats.get(p,0) for p in coalition); merged[c]=b.seats.get(name,0)
    changes={c:merged[c]-separate[c] for c in separate}
    return {"scenario":{"scenario_type":"coalition","territorial_distribution":"sum_by_province","assumptions":["no vote transfer","same turnout"],"source":"input_dataset"},
            "coalition":"+ ".join(coalition).replace("+ ","+"),"separate_seats_by_constituency":separate,
            "coalition_seats_by_constituency":merged,"delta_by_constituency":changes,
            "total_separate":sum(separate.values()),"total_coalition":sum(merged.values()),"delta":sum(changes.values())}
