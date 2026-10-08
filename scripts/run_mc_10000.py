#!/usr/bin/env python3
"""Independent 10,000-draw electoral Monte Carlo engine gate."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
import numpy as np
import pandas as pd
from src.electoral import allocate
ROOT=Path(__file__).resolve().parents[1]; SOURCE=ROOT/"data/resultados_oficiales_2004_2023.csv"; SEATS=ROOT/"data/2023_circunscripciones_oficiales.csv"; OUT=ROOT/"ci_evidence/mc_10000.json"; SEED=20261008; N=10000
def main():
    if not SOURCE.is_file() or not SEATS.is_file(): raise SystemExit("BLOCKED: canonical electoral inputs missing")
    df=pd.read_csv(SOURCE); required={"fecha_eleccion","circunscripcion","partido","votos","escaños"}
    if not required.issubset(df.columns): raise SystemExit("BLOCKED: historical source schema incomplete")
    d=df[df["fecha_eleccion"].astype(str).str[:10].eq("2019-11-10")].copy()
    if d.empty: raise SystemExit("BLOCKED: 2019N election missing")
    d["votos"]=pd.to_numeric(d["votos"],errors="raise").astype(int)
    s=pd.read_csv(SEATS); s["escanos_2023"]=pd.to_numeric(s["escanos_2023"],errors="raise").astype(int)
    if len(s)!=52 or int(s["escanos_2023"].sum())!=350: raise SystemExit("BLOCKED: seat structure must be 52/350")
    def norm(x): return {"Alicante/Alacant":"Alicante","Balears, Illes":"Illes Balears","Castellón/Castelló":"Castellón"}.get(str(x),str(x))
    d["prov"]=d["circunscripcion"].map(norm); s["prov"]=s["circunscripcion"].map(norm)
    groups={}
    for prov,g in d.groupby("prov"):
        parties=sorted(g["partido"].astype(str)); votes={p:int(v) for p,v in zip(g["partido"].astype(str),g["votos"])}; blank=0
        groups[prov]=(parties,votes,blank)
    if set(groups)!=set(s["prov"]): raise SystemExit("BLOCKED: 2019N/seat constituency mismatch")
    rng=np.random.Generator(np.random.PCG64(SEED)); seat_sums=np.empty(N,dtype=np.int16); status_counts={}
    for i in range(N):
        total_seats=0
        for prov,(parties,votes,blank) in groups.items():
            total=max(sum(votes.values()),1); p=np.array([v/total for v in votes.values()],dtype=float); draw=rng.dirichlet(np.maximum(p*80.0,0.05))
            dv={party:int(round(float(frac)*total)) for party,frac in zip(parties,draw)}; diff=total-sum(dv.values())
            if diff: dv[max(dv,key=dv.get)]+=diff
            valid=sum(dv.values())+blank; seat_n=int(s.loc[s["prov"].eq(prov),"escanos_2023"].iloc[0])
            a=allocate(dv,seat_n,valid,special=prov if prov in {"Ceuta","Melilla"} else "",blank_votes=blank)
            status_counts[a.status]=status_counts.get(a.status,0)+1
            if a.status!="OK": raise SystemExit(f"BLOCKED: allocation {prov} {a.status}")
            total_seats+=sum(a.seats.values())
        seat_sums[i]=total_seats
    if not np.all(seat_sums==350): raise SystemExit("BLOCKED: a draw did not allocate exactly 350 seats")
    result={"schema":"ELECTORAL_MONTE_CARLO_10000_V2","status":"PASS","iterations":N,"seed":SEED,"rng":"numpy.PCG64","constituencies":52,"seats":350,"source_sha256":hashlib.sha256(SOURCE.read_bytes()).hexdigest(),"seat_structure_sha256":hashlib.sha256(SEATS.read_bytes()).hexdigest(),"invariants":{"every_draw_seat_sum_350":True,"all_allocations_status_OK":True},"allocation_calls":N*52,"status_counts":status_counts,"predictive_claim":False}
    OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=="__main__": main()
