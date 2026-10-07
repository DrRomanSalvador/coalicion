"""Expanding-window OOS pipeline for canonical historical CIS observations."""
from __future__ import annotations
import csv,re
from datetime import date
from pathlib import Path
from .bias_filter import Observation, select_best
from .poll_error import PollObservation
from .context_corrections import select

ELECTIONS=(("2004-03-14","2004"),("2008-03-09","2008"),("2011-11-20","2011"),("2015-12-20","2015"),("2016-06-26","2016"),("2019-04-28","2019A"),("2019-11-10","2019N"),("2023-07-23","2023J"))
CANONICAL={"fecha_encuesta","partido","estimacion_voto","tipo_encuesta","fuente","codigo_estudio"}
LEGACY={"election","election_date","party","poll","actual","house","field_end","source","poll_id"}
ALIAS={"psoe":"PSOE","partido socialista obrero espanol":"PSOE","pp":"PP","partido popular":"PP","vox":"VOX","sumar":"SUMAR","podemos":"PODEMOS","iu":"IU","izquierda unida":"IU","cs":"CS","ciudadanos":"CS","erc":"ERC","esquerra republicana de catalunya":"ERC","junts":"JUNTS","junts per catalunya":"JUNTS","pnv":"PNV","partido nacionalista vasco":"PNV","bildu":"EH_BILDU","eh bildu":"EH_BILDU","bng":"BNG","bloque nacionalista galego":"BNG"}

def _norm(v:str)->str:
    s=re.sub(r"[^a-z0-9 ]+"," ",v.lower()).strip(); s=re.sub(r"\s+"," ",s)
    return ALIAS.get(s,s.upper().replace(" ","_"))

def _next(d:date):
    for raw,code in ELECTIONS:
        if d < date.fromisoformat(raw): return raw,code
    return None

def _official(path:Path)->dict[tuple[str,str],float]:
    if not path.exists(): raise FileNotFoundError(f"official results required for canonical OOS: {path}")
    totals={}; national={}
    with path.open(newline="",encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            k=(r["election"],_norm(r["partido"])); v=float(r["votos"])
            totals[k]=totals.get(k,0.0)+v; national[k[0]]=national.get(k[0],0.0)+v
    return {k:100*v/national[k[0]] for k,v in totals.items() if national[k[0]]>0}

def _canonical(rows,actual_path):
    actuals=_official(actual_path); out=[]
    for r in rows:
        try: d=date.fromisoformat(r["fecha_encuesta"][:10]); estimate=float(r["estimacion_voto"])
        except (KeyError,TypeError,ValueError): continue
        target=_next(d)
        if not target: continue
        ed,election=target; party=_norm(r["partido"]); actual=actuals.get((election,party))
        if actual is None: continue
        out.append(PollObservation(election=election,election_date=ed,party=party,poll=estimate,actual=actual,house="Congreso",field_end=r["fecha_encuesta"][:10],source=r["fuente"],poll_id=f"{r['codigo_estudio']}:{party}"))
    if not out: raise ValueError("canonical CIS dataset produced zero pre-election OOS observations")
    return out

def _legacy(rows):
    missing=LEGACY-set(rows[0])
    if missing: raise ValueError(f"legacy OOS dataset missing columns: {sorted(missing)}")
    return [PollObservation(election=r["election"],election_date=r["election_date"],party=r["party"],poll=float(r["poll"]),actual=float(r["actual"]),house=r["house"],field_end=r["field_end"],source=r["source"],poll_id=r["poll_id"],governing_party=r.get("governing_party",""),government_status=r.get("government_status",""),government_change=r.get("government_change","")) for r in rows]

def load_poll_observations(path:str|Path)->list[PollObservation]:
    p=Path(path)
    if not p.exists(): raise FileNotFoundError(f"dataset OOS inexistente: {p}")
    with p.open(newline="",encoding="utf-8") as fh: rows=list(csv.DictReader(fh))
    if not rows: raise ValueError(f"dataset OOS vacío: {p}")
    cols=set(rows[0])
    return _canonical(rows,p.with_name("resultados_oficiales_2004_2023.csv")) if CANONICAL.issubset(cols) else _legacy(rows)

def run_oos(rows:list[PollObservation])->dict:
    if len({r.election for r in rows})<2: raise ValueError("OOS requiere al menos dos elecciones")
    correction=select_best([Observation(r.election,r.party,r.poll,r.actual,r.house,r.field_end) for r in rows])
    return {"status":"PASS","n_rows":len(rows),"n_elections":len({r.election for r in rows}),"selected_bias_correction":correction.name,"selected_context_correction":select(rows),"contract":"EXPANDING_WINDOW_NO_FUTURE_LEAKAGE"}
