#!/usr/bin/env python3
"""2023 territorial baseline from canonical official Interior results.

The target election is evaluated against a persistence baseline trained only
on 2019N. Actual 2023 seats are read from the official materialization; all
predicted seats are allocated with the canonical electoral engine.
"""
from __future__ import annotations
import hashlib, json, re
from pathlib import Path
import numpy as np
import pandas as pd

from src.electoral import allocate

ROOT = Path(__file__).resolve().parents[1]
OFFICIAL = ROOT / "data" / "resultados_oficiales_2004_2023.csv"
SEATS = ROOT / "data" / "2023_circunscripciones_oficiales.csv"
OUT = ROOT / "ci_evidence" / "backtest_2023_baseline.json"
SEED = 20261006
N_SIM = 10_000

def norm_constituency(value: str) -> str:
    s = re.sub(r"^\s*\d+\s*-\s*", "", str(value)).strip()
    aliases = {
        "Alicante/Alacant":"Alicante",
        "Araba/Álava":"Araba/Álava",
        "Álava/Araba":"Araba/Álava",
        "Bizkaia":"Bizkaia",
        "Vizcaya/Bizkaia":"Bizkaia",
        "Castellón/Castelló":"Castellón",
        "Guipúzcoa/Gipuzkoa":"Gipuzkoa",
        "Islas Baleares/Illes Balears":"Illes Balears",
        "Balears, Illes":"Illes Balears",
        "La Coruña/A Coruña":"A Coruña",
        "Navarra/Nafarroa":"Navarra",
        "Orense/Ourense":"Ourense",
        "Valencia/València":"Valencia",
    }
    return aliases.get(s, s)

def label_kind(label: str) -> str:
    s = re.sub(r"[^a-z0-9 ]+", " ", str(label).lower()).strip()
    if "nulo" in s:
        return "NULL"
    if "blanco" in s:
        return "BLANK"
    if "abstencion" in s:
        return "ABSTENTION"
    if "total" in s:
        return "TOTAL"
    return "PARTY"

def party_label(label: str) -> str:
    parts = str(label).split(" - ", 1)
    return parts[1].strip() if len(parts) == 2 else str(label).strip()

if not OFFICIAL.is_file():
    raise SystemExit(f"Missing canonical official results: {OFFICIAL}")
if not SEATS.is_file():
    raise SystemExit(f"Missing canonical seat structure: {SEATS}")

df = pd.read_csv(OFFICIAL)
required = {"election","fecha_eleccion","circunscripcion","partido","votos","escaños"}
if not required.issubset(df.columns):
    raise SystemExit(f"Official results missing columns: {sorted(required-set(df.columns))}")
df["votos"] = pd.to_numeric(df["votos"], errors="raise").astype(int)
df["prov"] = df["circunscripcion"].map(norm_constituency)
df["kind"] = df["partido"].map(label_kind)
df["party"] = df["partido"].map(party_label)

seats = pd.read_csv(SEATS)
seats["escanos_2023"] = pd.to_numeric(seats["escanos_2023"], errors="raise").astype(int)
seats["prov"] = seats["circunscripcion"].map(norm_constituency)
if int(seats["escanos_2023"].sum()) != 350:
    raise SystemExit("seat structure does not sum to 350")

def election_matrix_by_date(election_date: str):
    x = df[df["fecha_eleccion"].astype(str).str[:10].eq(election_date)].copy()
    if x.empty:
        raise SystemExit(f"official election missing: {election_date}")
    parties = x[x["kind"].eq("PARTY")].groupby(["prov","party"],as_index=False)["votos"].sum()
    blanks = x[x["kind"].eq("BLANK")].groupby("prov")["votos"].sum().to_dict()
    nulls = x[x["kind"].eq("NULL")].groupby("prov")["votos"].sum().to_dict()
    valid = parties.groupby("prov")["votos"].sum().to_dict()
    for prov,v in blanks.items():
        valid[prov] = valid.get(prov,0) + int(v)
    return parties, valid, blanks, nulls

train_p, train_valid, train_blank, _ = election_matrix_by_date("2019-11-10")
target_p, target_valid, target_blank, _ = election_matrix_by_date("2023-07-23")

seat_provs=set(seats["prov"])
target_provs=set(target_p["prov"])
if target_provs != seat_provs:
    raise SystemExit(
        "2023 constituency scope mismatch: "
        f"missing_from_results={sorted(seat_provs-target_provs)} "
        f"extra_in_results={sorted(target_provs-seat_provs)}"
    )

train_maps={p:dict(zip(g["party"],g["votos"])) for p,g in train_p.groupby("prov")}
target_maps={p:dict(zip(g["party"],g["votos"])) for p,g in target_p.groupby("prov")}

# Actual seats are official certified results, not reconstructed prediction.
actual_rows=df[(df["election"].astype(str).eq("2023")) & (df["kind"].eq("PARTY"))]
actual_seats=actual_rows.groupby("party")["escaños"].sum().astype(int).to_dict()
if sum(actual_seats.values()) != 350:
    raise SystemExit(f"official 2023 seats do not sum to 350: {sum(actual_seats.values())}")

# Persistence national vote-share baseline: only 2019N observations.
parties=sorted(set(target_p["party"]))
train_votes={p:0 for p in parties}
target_votes={p:0 for p in parties}
for prov,m in train_maps.items():
    for p,v in m.items():
        if p in train_votes: train_votes[p]+=int(v)
for prov,m in target_maps.items():
    for p,v in m.items():
        if p in target_votes: target_votes[p]+=int(v)
train_valid_total=sum(train_valid.values())
target_valid_total=sum(target_valid.values())
vote_rows=[]
for p in parties:
    actual=100*target_votes[p]/target_valid_total
    pred=100*train_votes[p]/train_valid_total
    vote_rows.append((p,actual,pred))
arr=np.array([[a,b] for _,a,b in vote_rows],dtype=float)
vote_mae=float(np.mean(np.abs(arr[:,0]-arr[:,1])))
vote_rmse=float(np.sqrt(np.mean((arr[:,0]-arr[:,1])**2)))

# Exact territorial prediction engine. Ties are fail-closed; no lexicographic
# tie-breaking is introduced by this backtest.
def allocate_pred(votes, seat_n, valid, special):
    result=allocate({p:int(v) for p,v in votes.items()},seat_n,int(valid),special=special)
    if result.status!="OK":
        raise RuntimeError(f"territorial allocation blocked: {special} {result.status} {result.tie}")
    return result.seats

rng=np.random.Generator(np.random.PCG64(SEED))
sim_seats={p:np.zeros(N_SIM,dtype=np.int16) for p in parties}
for prov in sorted(train_maps):
    votes=train_maps[prov]
    valid=int(train_valid[prov])
    seat_n=int(seats.loc[seats["prov"].eq(prov),"escanos_2023"].iloc[0])
    ps=list(votes)
    counts=np.array([max(float(votes[p]),0.0) for p in ps],dtype=float)
    alpha=counts+1.0
    draws=rng.dirichlet(alpha,size=N_SIM)
    for i in range(N_SIM):
        dv={p:int(round(x*valid)) for p,x in zip(ps,draws[i])}
        # Preserve exact total after integer rounding by assigning residual to
        # the largest sampled category.
        residual=valid-sum(dv.values())
        if residual:
            winner=max(dv,key=dv.get)
            dv[winner]+=residual
        alloc=allocate_pred(dv,seat_n,valid,prov if prov in {"Ceuta","Melilla"} else "")
        for p,s in alloc.items():
            if p in sim_seats: sim_seats[p][i]+=s

medians=np.array([float(np.median(sim_seats[p])) for p in parties])
actual_vec=np.array([actual_seats.get(p,0) for p in parties],dtype=float)
seat_mae=float(np.mean(np.abs(actual_vec-medians)))
seat_rmse=float(np.sqrt(np.mean((actual_vec-medians)**2)))

intervals={}
winners=[p for p,s in actual_seats.items() if s>0]
covered=0
for p in winners:
    q=np.percentile(sim_seats[p],[10,50,90])
    intervals[p]={"actual":int(actual_seats[p]),"p10":float(q[0]),"p50":float(q[1]),"p90":float(q[2])}
    covered += int(q[0] <= actual_seats[p] <= q[2])
coverage=covered/len(winners) if winners else float("nan")

result={
 "election":"2023",
 "cutoff":"2019-11-10",
 "model":"baseline_persistence_2019N",
 "note":"Canonical official Interior results; no 2023 votes are used in prediction. Actual 2023 seats are ground truth; predicted seats use canonical electoral allocation.",
 "source_tier":"PRIMARY_OFFICIAL",
 "source_sha256":hashlib.sha256(OFFICIAL.read_bytes()).hexdigest(),
 "seat_structure_source":"data/2023_circunscripciones_oficiales.csv",
 "seat_structure_sha256":hashlib.sha256(SEATS.read_bytes()).hexdigest(),
 "mc_seed":SEED,
 "rng":"numpy.PCG64",
 "n_simulations":N_SIM,
 "metrics":{
   "mae_vote_national_pp":vote_mae,
   "rmse_vote_national_pp":vote_rmse,
   "mae_seats_median":seat_mae,
   "rmse_seats_median":seat_rmse,
   "coverage_actual_seats_in_p10_p90_winners":coverage,
   "n_2023_seat_winning_parties":len(winners)
 },
 "seat_intervals":intervals,
 "contracts":{
   "official_source":True,
   "seat_sum_350":True,
   "no_future_vote_input":True,
   "canonical_electoral_engine":True,
   "absolute_ties_fail_closed":True
 }
}
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(result,ensure_ascii=False,indent=2))
