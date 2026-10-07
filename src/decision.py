"""Orquestador mínimo: valida escenarios y delega cálculo en los motores canónicos."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from fractions import Fraction
import hashlib, json
from .coalition import coalition_result
@dataclass(frozen=True)
class Scenario:
    scenario_type:str
    party:str|None=None
    shift_type:str|None=None
    shift_value:float|None=None
    territorial_distribution:str="user_defined"
    assumptions:tuple[str,...]=()
    source:str="user_defined"
    uncertainty:str="none"

def validate_scenario(s:Scenario)->None:
    if s.scenario_type not in {"coalition","national_shift","territorial_shift"}: raise ValueError("scenario_type inválido")
    if s.scenario_type!="coalition" and s.shift_value is None: raise ValueError("shift_value obligatorio")
    if s.scenario_type=="national_shift" and s.territorial_distribution=="unspecified": raise ValueError("AMBIGUOUS_SCENARIO")

def sha256_json(obj)->str:
    return hashlib.sha256(json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def apply_absolute_shift(votes_by_constituency,party,shift_points,territorial_distribution):
    if territorial_distribution=="unspecified": raise ValueError("AMBIGUOUS_SCENARIO")
    if territorial_distribution!="uniform_by_province": raise ValueError("Solo uniform_by_province está implementado")
    out={}
    for c,row0 in votes_by_constituency.items():
        row=dict(row0)
        if party not in row: raise ValueError(f"{c}: candidatura ausente")
        total=sum(row.values()); delta=Fraction(str(shift_points))*total/Fraction(100)
        if delta.denominator!=1: raise ValueError("El shock produce votos no enteros; defina un redondeo explícito")
        row[party]+=int(delta)
        if row[party]<0: raise ValueError("El shock produciría votos negativos")
        out[c]=row
    return out

def evaluate_coalition(votes,seats,valid_votes,coalition,special=None,blank=None):
    return coalition_result(votes,seats,valid_votes,coalition,special,blank)
