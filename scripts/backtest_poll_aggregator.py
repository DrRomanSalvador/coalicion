#!/usr/bin/env python3
"""Backtest OOS del agregador de encuestas.

Si no existe un archivo con microdatos suficientes, devuelve BLOCKED y no fabrica
observaciones. Cuando exista, compara promedio simple contra el agregador ponderado
por muestra/recencia/historial y guarda métricas por elección.
"""
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd

from src.poll_aggregator import HistoricalError, PollEstimate, aggregate_party

INPUT = Path("data/encuestas_historicas_2004_2023.csv")
OUT = Path("artifacts/data/poll_aggregator_oos.json")
REQUIRED = {"election","election_date","party","poll","actual","house","field_end","poll_id","sample_size"}

def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if not INPUT.exists():
        result={"schema":"POLL_AGGREGATOR_OOS_V1","status":"BLOCKED","reason":"archivo de encuestas inexistente"}
        OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8"); print(json.dumps(result,ensure_ascii=False)); return 0
    df=pd.read_csv(INPUT)
    if df.empty:
        result={"schema":"POLL_AGGREGATOR_OOS_V1","status":"BLOCKED","reason":"archivo histórico versionado sin observaciones; no se inventan datos"}
        OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8"); print(json.dumps(result,ensure_ascii=False)); return 0
    missing=REQUIRED-set(df.columns)
    if missing:
        raise SystemExit("Faltan columnas obligatorias: "+",".join(sorted(missing)))
    for c in ("estimate_pct","sample_size","actual"):
        if c in df: df[c]=pd.to_numeric(df[c],errors="raise")
    df["sample_size"]=df["sample_size"].astype(int)
    df["election_date"]=df["election_date"].astype(str)
    df["field_end"]=df["field_end"].astype(str)

    elections=sorted(df["election"].unique(), key=lambda e: df.loc[df.election.eq(e),"election_date"].min())
    results=[]
    for election in elections:
        target_date=df.loc[df.election.eq(election),"election_date"].min()
        train=df[df.election_date < target_date]
        test=df[df.election.eq(election)]
        if train.empty: continue
        for party in sorted(test.party.unique()):
            cur=test[test.party.eq(party)]
            if cur.empty: continue
            simple=float(cur.estimate_pct.mean())
            polls=[PollEstimate(
                str(r.election),party,str(r.house),float(r.estimate_pct),
                str(r.field_end),int(r.sample_size),str(r.poll_id),str(r.source) if "source" in r else "",
                str(r.source_tier) if "source_tier" in r else ""
            ) for _,r in cur.iterrows()]
            hist=[HistoricalError(
                str(r.election),str(r.party),str(r.house),float(r.estimate_pct),float(r.actual),
                str(r.field_end),str(r.election_date)
            ) for _,r in train[train.party.eq(party)].iterrows()]
            try:
                agg=aggregate_party(polls,party,target_date,hist)
                weighted=agg.estimate_pct
            except ValueError:
                continue
            actual=float(cur.actual.iloc[0])
            results.append({
                "election":election,"party":party,"actual":actual,
                "simple_mean":simple,"weighted":weighted,
                "simple_abs_error":abs(simple-actual),
                "weighted_abs_error":abs(weighted-actual)
            })
    if not results:
        raise SystemExit("No hay observaciones OOS utilizables")
    out=pd.DataFrame(results)
    payload={
        "schema":"POLL_AGGREGATOR_OOS_V1","status":"COMPLETE",
        "rows":int(len(out)),"elections":sorted(out.election.unique()),
        "simple_mean_mae":float(out.simple_abs_error.mean()),
        "weighted_aggregator_mae":float(out.weighted_abs_error.mean()),
        "weighted_beats_simple":bool(out.weighted_abs_error.mean() < out.simple_abs_error.mean()),
        "by_election":out.groupby("election")[["simple_abs_error","weighted_abs_error"]].mean().to_dict("index"),
        "activation":"PENDING_STABILITY_REVIEW"
    }
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(payload,ensure_ascii=False,indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
