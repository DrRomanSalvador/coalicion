"""Canonical decision orchestration: explicit, auditable electoral scenarios."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from fractions import Fraction
from typing import Mapping
import hashlib, json
from .electoral import allocate

@dataclass(frozen=True)
class Scenario:
    scenario_type: str
    party: str | None = None
    shift_type: str | None = None
    shift_value: float | None = None
    territorial_distribution: str = "user_defined"
    assumptions: tuple[str, ...] = ()
    source: str = "user_defined"
    uncertainty: str = "none"

def sha256_json(obj) -> str:
    raw=json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
    return hashlib.sha256(raw).hexdigest()

def validate_scenario(s: Scenario) -> None:
    if s.scenario_type not in {"coalition","national_shift","territorial_shift"}:
        raise ValueError("scenario_type inválido")
    if s.scenario_type != "coalition" and s.shift_value is None:
        raise ValueError("shift_value obligatorio")
    if s.scenario_type == "national_shift" and s.territorial_distribution == "unspecified":
        raise ValueError("AMBIGUOUS_SCENARIO")

def coalition_result(votes_by_constituency: Mapping[str, Mapping[str,int]],
                     seats_by_constituency: Mapping[str,int],
                     valid_votes: Mapping[str,int],
                     coalition: tuple[str,...],
                     special: Mapping[str,str] | None=None,
                     blank: Mapping[str,int] | None=None) -> dict:
    if len(coalition)<2 or len(set(coalition))!=len(coalition):
        raise ValueError("coalición inválida")
    special=special or {}; blank=blank or {}
    separate={}; merged={}
    for c,row in votes_by_constituency.items():
        if any(p not in row for p in coalition): raise ValueError(f"{c}: candidatura ausente")
        a=allocate(row,seats_by_constituency[c],valid_votes[c],special.get(c,""),blank.get(c,0))
        if a.status!="OK": raise RuntimeError(f"BLOCKED:{c}:{a.status}")
        m=dict(row); name="+".join(coalition); m[name]=sum(m[p] for p in coalition)
        for p in coalition: del m[p]
        b=allocate(m,seats_by_constituency[c],valid_votes[c],special.get(c,""),blank.get(c,0))
        if b.status!="OK": raise RuntimeError(f"BLOCKED:{c}:{b.status}")
        separate[c]=sum(a.seats.get(p,0) for p in coalition)
        merged[c]=b.seats.get(name,0)
    changes={c:merged[c]-separate[c] for c in separate}
    return {"scenario":asdict(Scenario("coalition",territorial_distribution="sum_by_province",assumptions=("no vote transfer","same turnout"),source="input_dataset")),"coalition":"+".join(coalition),"separate_seats_by_constituency":separate,"coalition_seats_by_constituency":merged,"delta_by_constituency":changes,"total_separate":sum(separate.values()),"total_coalition":sum(merged.values()),"delta":sum(changes.values()),"changed_constituencies":[c for c,d in changes.items() if d],"certificate_input_hash":sha256_json(votes_by_constituency)}

def apply_absolute_shift(votes_by_constituency, party, shift_points: float, territorial_distribution: str) -> dict:
    if territorial_distribution == "unspecified": raise ValueError("AMBIGUOUS_SCENARIO")
    if territorial_distribution != "uniform_by_province": raise ValueError("Solo uniform_by_province está implementado")
    out={}
    for c,row0 in votes_by_constituency.items():
        row=dict(row0); total=sum(row.values())
        if party not in row: raise ValueError(f"{c}: candidatura ausente")
        delta=Fraction(str(shift_points))*total/Fraction(100)
        if delta.denominator != 1: raise ValueError("El shock produce votos no enteros; defina un redondeo explícito")
        row[party]+=int(delta)
        if row[party]<0: raise ValueError("El shock produciría votos negativos")
        out[c]=row
    return out
