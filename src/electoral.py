"""Motor electoral español exacto, fail-closed y reproducible."""
from __future__ import annotations
from dataclasses import dataclass
from fractions import Fraction
from typing import Callable, Mapping, Optional
from pathlib import Path
import csv

@dataclass(frozen=True)
class Allocation:
    seats: dict[str, int]
    status: str
    tie: tuple[str, ...] = ()

def _validate_common(votes: Mapping[str, int]) -> None:
    if not isinstance(votes, Mapping): raise TypeError("votes debe ser un mapping")
    if any(not isinstance(p, str) or not p.strip() for p in votes): raise ValueError("nombres inválidos")
    if any(isinstance(v,bool) or not isinstance(v,int) or v<0 for v in votes.values()): raise ValueError("votos inválidos")

def valid_votes(votes: Mapping[str,int], blank_votes:int=0)->int:
    _validate_common(votes)
    if isinstance(blank_votes,bool) or not isinstance(blank_votes,int) or blank_votes<0: raise ValueError("blank_votes inválido")
    return sum(votes.values())+blank_votes

def _validate_matrix(votes, valid, blank):
    if isinstance(valid,bool) or not isinstance(valid,int) or valid<=0: raise ValueError("valid_votes inválido")
    if valid_votes(votes,blank)!=valid: raise ValueError("candidaturas + blancos debe coincidir con votos válidos")

def _eligible(votes, valid, threshold):
    return {p:v for p,v in votes.items() if Fraction(v,valid)>=threshold}

def dhondt(votes:Mapping[str,int], seats:int, valid_votes_total:int, blank_votes:int=0, threshold:Fraction=Fraction(3,100), tie_breaker:Optional[Callable[[tuple[str,...]], str]]=None)->Allocation:
    if isinstance(seats,bool) or not isinstance(seats,int) or seats<1: raise ValueError("seats inválido")
    if not 0<=threshold<=1: raise ValueError("threshold inválido")
    _validate_matrix(votes,valid_votes_total,blank_votes)
    result={p:0 for p in votes}
    eligible=_eligible(votes,valid_votes_total,threshold)
    tie_state: dict[frozenset[str], str] = {}
    if not eligible: return Allocation(result,"INSUFICIENTES_CANDIDATURAS")
    for _ in range(seats):
        qs={p:Fraction(v,result[p]+1) for p,v in eligible.items()}
        top=max(qs.values()); tied=[p for p,q in qs.items() if q==top]
        if len(tied)>1:
            max_votes=max(eligible[p] for p in tied); tied=[p for p in tied if eligible[p]==max_votes]
            if len(tied)>1:
                tied_tuple=tuple(sorted(tied))
                if tie_breaker is None:
                    return Allocation(result,"EMPATE_ABSOLUTO_PENDIENTE",tied_tuple)
                if len(tied_tuple)!=2:
                    return Allocation(result,"EMPATE_ABSOLUTO_PENDIENTE",tied_tuple)
                key=frozenset(tied_tuple)
                previous=tie_state.get(key)
                if previous is None:
                    chosen=tie_breaker(tied_tuple)
                    if chosen not in tied_tuple:
                        raise ValueError("tie_breaker devolvió una candidatura no empatada")
                    tie_state[key]=chosen
                else:
                    chosen=tied_tuple[1] if previous==tied_tuple[0] else tied_tuple[0]
                    tie_state[key]=chosen
                tied=[chosen]
        result[tied[0]]+=1
    return Allocation(result,"OK")

def ceuta_melilla(votes:Mapping[str,int], valid_votes_total:Optional[int]=None, blank_votes:int=0, tie_breaker:Optional[Callable[[tuple[str,...]], str]]=None)->Allocation:
    _validate_common(votes)
    if not votes: raise ValueError("sin candidaturas")
    if valid_votes_total is not None: _validate_matrix(votes,valid_votes_total,blank_votes)
    winners=[p for p,v in votes.items() if v==max(votes.values())]
    if len(winners)>1:
        tied=tuple(sorted(winners))
        if tie_breaker is None:
            return Allocation({p:0 for p in votes},"EMPATE_MAYORIA_PENDIENTE",tied)
        chosen=tie_breaker(tied)
        if chosen not in tied:
            raise ValueError("tie_breaker devolvió una candidatura no empatada")
        return Allocation({p:int(p==chosen) for p in votes},"OK",tied)
    return Allocation({p:int(p==winners[0]) for p in votes},"OK")

def allocate(votes,seats,valid_votes_total,special="",blank_votes=0,tie_breaker=None):
    if special in {"Ceuta","Melilla"}:
        if seats!=1: raise ValueError("Ceuta/Melilla: 1 escaño")
        return ceuta_melilla(votes,valid_votes_total,blank_votes,tie_breaker=tie_breaker)
    return dhondt(votes,seats,valid_votes_total,blank_votes,tie_breaker=tie_breaker)

def merge_candidacies(*matrices):
    out={}
    for m in matrices:
        _validate_common(m)
        for p,v in m.items(): out[p]=out.get(p,0)+v
    return out

def official_2026_seats() -> dict[str, int]:
    path = Path(__file__).resolve().parents[1] / "data" / "2026_circunscripciones_oficiales.csv"
    if not path.is_file():
        raise RuntimeError("BLOCKED: falta la tabla oficial de magnitudes 2026")
    out = {}
    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row.get("source") != "BOE-A-2026-20742":
                raise RuntimeError("BLOCKED: fuente BOE inesperada en magnitudes 2026")
            name = str(row.get("circunscripcion") or "").strip()
            seats = int(row.get("escanos_2026") or 0)
            if not name or seats < 1 or name in out:
                raise RuntimeError("BLOCKED: tabla de magnitudes 2026 inválida")
            out[name] = seats
    if len(out) != 52 or sum(out.values()) != 350 or out.get("Ceuta") != 1 or out.get("Melilla") != 1:
        raise RuntimeError("BLOCKED: magnitudes oficiales 2026 no suman 52/350")
    return out

def allocate_congress(constituencies,seats_by_constituency,blank_votes_by_constituency,special_by_constituency=None):
    special_by_constituency=special_by_constituency or {}
    official_2026 = official_2026_seats()
    official = set(seats_by_constituency)
    if official != set(official_2026):
        raise ValueError("las circunscripciones no coinciden exactamente con la tabla oficial 2026")
    if dict(seats_by_constituency) != official_2026:
        raise ValueError("la magnitud de alguna circunscripción no coincide con BOE-A-2026-20742")
    if set(constituencies)!=official or official!=set(blank_votes_by_constituency):
        raise ValueError("claves de circunscripción no coinciden")
    if special_by_constituency.get("Ceuta") != "Ceuta" or special_by_constituency.get("Melilla") != "Melilla":
        raise ValueError("Ceuta/Melilla deben estar marcadas como circunscripciones especiales")
    national={}
    for c,votes in constituencies.items():
        a=allocate(votes,seats_by_constituency[c],valid_votes(votes,blank_votes_by_constituency[c]),special_by_constituency.get(c,""),blank_votes_by_constituency[c])
        if a.status!="OK": raise RuntimeError(f"asignación bloqueada en {c}: {a.status}")
        for p,s in a.seats.items(): national[p]=national.get(p,0)+s
    if sum(national.values())!=350: raise AssertionError("resultado no suma 350")
    return national
