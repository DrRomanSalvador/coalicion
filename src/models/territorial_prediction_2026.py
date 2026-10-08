"""Deterministic 2026 territorial demo model.

Uses current national survey evidence plus the spatial pattern of the official
2023 constituency matrix. It is explicitly a MODELLED territorial estimate,
not an observed territorial poll and not an independently calibrated 2026
forecast.
"""
from __future__ import annotations
import csv, hashlib, json, math
from pathlib import Path
from typing import Any
from src.electoral import allocate

FAMILIES={"PP":"PP","PSOE":"PSOE","Vox":"Vox","Sumar":"Sumar"}

def family(name:str)->str|None:
    u=name.upper()
    if "PP " in u or u.startswith("PP") or "PARTIDO POPULAR" in u: return "PP"
    if "PSOE" in u or "PARTIDO SOCIALISTA OBRERO" in u or "PSC " in u or "PSE-EE" in u or "PSDEG" in u or "PSIB-PSOE" in u: return "PSOE"
    if "VOX" in u: return "Vox"
    if "SUMAR" in u or "ECP " in u or "COMPROMÍS" in u and "SUMAR" in u: return "Sumar"
    return None

def h(x:Any)->str:
    return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def load_seats(path:Path)->dict[str,int]:
    out={}
    with path.open(encoding="utf-8",newline="") as f:
        for row in csv.DictReader(f):
            out[row["circunscripcion"]]=int(row["escanos_2026"])
    if len(out)!=52 or sum(out.values())!=350: raise RuntimeError("BLOCKED_INVALID_2026_SEATS")
    return out

def _norm(name:str)->str:
    aliases={"Coruña (A)":"A Coruña","Balears (Illes)":"Balears, Illes","Palmas (Las)":"Las Palmas","Rioja (La)":"La Rioja"}
    return aliases.get(name,name)

def load_2023(path:Path)->dict[str,dict[str,Any]]:
    x=json.loads(path.read_text(encoding="utf-8"))
    return x["data"]["constituencies"]

def predict(*,survey_path:Path,canonical_2023:Path,seats_path:Path,output:Path)->dict[str,Any]:
    surveys=json.loads(survey_path.read_text(encoding="utf-8"))["surveys"]
    if len(surveys)<10: raise RuntimeError("BLOCKED_CURRENT_SURVEY_COUNT")
    targets={p:sum(s["shares"][p] for s in surveys)/len(surveys)/100 for p in FAMILIES}
    rows=load_2023(canonical_2023); seats=load_seats(seats_path)
    by={}
    for c,old in rows.items():
        c2=_norm(c)
        if c2 not in seats: continue
        oldvotes=old["parties"]; total=sum(oldvotes.values())
        oldfam={p:sum(v for n,v in oldvotes.items() if family(n)==p) for p in FAMILIES}
        old_other=max(0,total-sum(oldfam.values()))
        current={}
        for p in FAMILIES:
            base=oldfam[p]/total if total else 0
            # national swing: preserve 2023 spatial distribution within each family
            current[p]=max(0,round(total*targets[p]* (base/(sum(oldfam.values())/total) if sum(oldfam.values()) else 0)))
        allocated=sum(current.values())
        residual=max(0,total-allocated)
        for n,v in oldvotes.items():
            if family(n) is None:
                current[n]=round(v/old_other*residual) if old_other else 0
        diff=total-sum(current.values())
        if diff:
            current["OTHER_RESIDUAL"]=current.get("OTHER_RESIDUAL",0)+diff
        blank=int(old.get("blank_votes",0))
        valid=sum(current.values())+blank
        special=c2 if c2 in {"Ceuta","Melilla"} else ""
        tie=lambda tied: sorted(tied)[int(h({"c":c2,"t":tied})[-1],16)%2]
        a=allocate(current,seats[c2],valid,special,blank,tie_breaker=tie)
        if a.status!="OK": raise RuntimeError(f"BLOCKED_ALLOCATION:{c2}:{a.status}")
        by[c2]={"seats":seats[c2],"votes":dict(sorted(current.items())),"seat_allocation":a.seats}
    national={}
    for row in by.values():
        for p,n in row["seat_allocation"].items(): national[p]=national.get(p,0)+n
    result={"schema":"TERRITORIAL_PREDICTION_2026_DEMO_V1","status":"PASS","mode":"MODELLED_DEMO_NON_OFFICIAL",
            "as_of":"2026-10-08","method":"national_current_survey_mean_plus_2023_constituency_spatial_pattern",
            "observed_territorial_polls":0,"territorial_input":"MODELLED_NOT_OBSERVED","calibration_status":"NOT_2026_CALIBRATED",
            "current_survey_count":len(surveys),"constituencies":by,"national_seats":dict(sorted(national.items())),
            "seat_total":sum(national.values()),"survey_input_hash":h(surveys),
            "output_hash":h({"constituencies":by,"national_seats":national}),
            "limitations":["No se presenta como encuesta territorial observada.","No es calibración probabilística 2026.","La auditoría externa independiente sigue pendiente."],
            "fail_closed":True}
    output.parent.mkdir(parents=True,exist_ok=True); output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return result
