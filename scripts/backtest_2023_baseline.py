#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, math
from pathlib import Path
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd

SEED = 20261006
N_SIM = 10_000
ROOT = Path(".audit_historico")
DATA = ROOT / "historical_province_secondary.csv"
SEATS_URL = "https://raw.githubusercontent.com/DrRomanSalvador/coalicion/main/data/2023_circunscripciones_oficiales.csv"
SEATS_FILE = ROOT / "seats_2023.csv"

if not DATA.exists():
    raise SystemExit("Missing historical staged dataset")

req = Request(SEATS_URL, headers={"User-Agent":"SEEC-backtest/1.0"})
with urlopen(req, timeout=60) as resp:
    SEATS_FILE.write_bytes(resp.read())

seats = pd.read_csv(SEATS_FILE)
seats["escanos_2023"] = seats["escanos_2023"].astype(int)
if int(seats["escanos_2023"].sum()) != 350:
    raise SystemExit("2023 seat structure does not sum to 350")

df = pd.read_csv(DATA)
for c in ["ballots","blank_ballots","party_ballots","valid_ballots","total_ballots"]:
    df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
df["party"] = df["abbrev_candidacies"].fillna(df["name_candidacies"]).astype(str).str.strip()
df["prov"] = df["prov"].astype(str).str.strip().replace(PROV_MAP)
PROV_MAP = {
    "Alicante/Alacant":"Alicante","Araba/Álava":"Araba/Álava","Álava/Araba":"Araba/Álava",
    "Bizkaia":"Bizkaia","Vizcaya/Bizkaia":"Bizkaia",
    "Castellón/Castelló":"Castellón","Guipúzcoa/Gipuzkoa":"Gipuzkoa",
    "Islas Baleares/Illes Balears":"Illes Balears","La Coruña/A Coruña":"A Coruña",
    "Navarra/Nafarroa":"Navarra","Orense/Ourense":"Ourense",
    "Valencia/València":"Valencia",
}

train = df[df["election"].eq("2019N")].copy()
target = df[df["election"].eq("2023")].copy()

if train.empty or target.empty:
    raise SystemExit("2019N/2023 data missing")
if set(seats["circunscripcion"]) != set(target["prov"].unique()):
    missing = sorted(set(seats["circunscripcion"]) - set(target["prov"].unique()))
    extra = sorted(set(target["prov"].unique()) - set(seats["circunscripcion"]))
    raise SystemExit(f"Province mismatch. missing={missing} extra={extra}")

# Aggregate repeated candidacy rows within each province.
train_p = train.groupby(["prov","party"], as_index=False).agg(votes=("ballots","sum"))
train_tot = train.groupby("prov", as_index=False).agg(valid=("valid_ballots","first"))
target_p = target.groupby(["prov","party"], as_index=False).agg(votes=("ballots","sum"))
target_tot = target.groupby("prov", as_index=False).agg(valid=("valid_ballots","first"))

# Cross-check the secondary source's province totals against the 2023 seat file.
cross = target_tot.merge(
    seats[["circunscripcion","votos_validos_2023"]],
    left_on="prov", right_on="circunscripcion", how="inner"
)
cross["diff_valid"] = cross["valid"] - cross["votos_validos_2023"]
if len(cross) != 52 or cross["diff_valid"].abs().max() > 1:
    raise SystemExit(
        f"2023 valid-vote crosscheck failed: cells={len(cross)}, "
        f"max_abs_diff={cross['diff_valid'].abs().max()}"
    )

def dhondt(votes: dict[str,float], seats_n: int, valid: float) -> dict[str,int]:
    if seats_n <= 0:
        return {}
    eligible = {p:v for p,v in votes.items() if v >= 0.03 * valid}
    alloc = {p:0 for p in eligible}
    for _ in range(seats_n):
        if not eligible:
            break
        # Deterministic legal ordering: quotient descending, then total votes.
        best = max(eligible, key=lambda p: (eligible[p] / (alloc[p] + 1), eligible[p]))
        alloc[best] += 1
    return alloc

def special_single(votes: dict[str,float]) -> dict[str,int]:
    if not votes:
        return {}
    best = max(votes, key=lambda p: (votes[p], p))
    return {best:1}

# Actual 2023 seats from the staged vote matrix.
actual_seats: dict[str,int] = {}
for prov, g in target_p.groupby("prov"):
    vv = float(target_tot.loc[target_tot["prov"].eq(prov), "valid"].iloc[0])
    seat_n = int(seats.loc[seats["circunscripcion"].eq(prov), "escanos_2023"].iloc[0])
    votes = dict(zip(g["party"], g["votes"]))
    alloc = special_single(votes) if prov in {"Ceuta","Melilla"} else dhondt(votes, seat_n, vv)
    for p,s in alloc.items():
        actual_seats[p] = actual_seats.get(p,0) + s
if sum(actual_seats.values()) != 350:
    raise SystemExit(f"Derived actual 2023 seats do not sum to 350: {sum(actual_seats.values())}")

# Strict no-leakage baseline: persistence of 2019N candidacy vote counts.
# No 2023 turnout or 2023 vote shares are used in the prediction.
train_maps = {}
for prov, g in train_p.groupby("prov"):
    train_maps[prov] = dict(zip(g["party"], g["votes"]))

parties = sorted(set(target_p["party"]))
actual_vote = target_p.groupby("party")["votes"].sum().to_dict()
actual_valid = float(target_tot["valid"].sum())

# National baseline point prediction.
pred_vote = {}
for prov, votes in train_maps.items():
    for p,v in votes.items():
        pred_vote[p] = pred_vote.get(p,0.0) + float(v)
pred_valid = float(train_tot["valid"].sum())
vote_rows = []
for p in parties:
    a = actual_vote.get(p,0.0) / actual_valid * 100.0
    b = pred_vote.get(p,0.0) / pred_valid * 100.0
    vote_rows.append((p,a,b))
vote_arr = np.array([[a,b] for _,a,b in vote_rows])
vote_mae = float(np.mean(np.abs(vote_arr[:,0]-vote_arr[:,1])))
vote_rmse = float(np.sqrt(np.mean((vote_arr[:,0]-vote_arr[:,1])**2)))

rng = np.random.Generator(np.random.PCG64(SEED))
sim_seats = {p: np.zeros(N_SIM, dtype=np.int16) for p in parties}

# Monte Carlo: Dirichlet posterior around 2019N province shares.
for prov in sorted(train_maps):
    votes = train_maps[prov]
    train_valid = float(train_tot.loc[train_tot["prov"].eq(prov), "valid"].iloc[0])
    seat_n = int(seats.loc[seats["circunscripcion"].eq(prov), "escanos_2023"].iloc[0])
    ps = list(votes)
    counts = np.array([max(float(votes[p]),0.0) for p in ps], dtype=float)
    alpha = counts + 1.0
    if prov in {"Ceuta","Melilla"}:
        draws = rng.dirichlet(alpha, size=N_SIM)
        for i in range(N_SIM):
            dv = dict(zip(ps, draws[i] * train_valid))
            alloc = special_single(dv)
            for p,s in alloc.items():
                if p in sim_seats: sim_seats[p][i] += s
        continue
    draws = rng.dirichlet(alpha, size=N_SIM)
    for i in range(N_SIM):
        dv = dict(zip(ps, draws[i] * train_valid))
        alloc = dhondt(dv, seat_n, train_valid)
        for p,s in alloc.items():
            if p in sim_seats: sim_seats[p][i] += s

seat_metrics = []
for p in parties:
    actual = actual_seats.get(p,0)
    med = float(np.median(sim_seats[p]))
    seat_metrics.append((p, actual, med))

actual_vec = np.array([x[1] for x in seat_metrics], dtype=float)
med_vec = np.array([x[2] for x in seat_metrics], dtype=float)
seat_mae = float(np.mean(np.abs(actual_vec-med_vec)))
seat_rmse = float(np.sqrt(np.mean((actual_vec-med_vec)**2)))

seat_winners = [p for p,s in actual_seats.items() if s > 0]
covered = 0
intervals = {}
for p in seat_winners:
    arr = sim_seats.get(p, np.zeros(N_SIM, dtype=np.int16))
    p10,p50,p90 = np.percentile(arr,[10,50,90])
    intervals[p] = {"actual":int(actual_seats[p]),"p10":float(p10),"p50":float(p50),"p90":float(p90)}
    covered += int(p10 <= actual_seats[p] <= p90)
coverage = covered / len(seat_winners) if seat_winners else float("nan")

manifest = json.loads((ROOT/"secondary_manifest.json").read_text(encoding="utf-8"))
result = {
    "election":"2023",
    "cutoff":"2019-11-10",
    "model":"baseline_persistence_2019N",
    "note":"Explicit baseline, not the SEEC territorial Bayesian model. Exact 2019N candidacy labels persist; no 2023 vote/turnout information is used in prediction.",
    "source_tier":"SECONDARY_REPLICA",
    "source_sha256":manifest["source_sha256"],
    "seat_structure_source":SEATS_URL,
    "seat_structure_sha256":hashlib.sha256(SEATS_FILE.read_bytes()).hexdigest(),
    "mc_seed":SEED,
    "rng":"numpy.PCG64",
    "n_simulations":N_SIM,
    "metrics":{
        "mae_vote_national_pp":vote_mae,
        "rmse_vote_national_pp":vote_rmse,
        "mae_seats_median":seat_mae,
        "rmse_seats_median":seat_rmse,
        "coverage_actual_seats_in_p10_p90_winners":coverage,
        "n_2023_seat_winning_parties":len(seat_winners)
    },
    "seat_intervals":intervals,
    "crosscheck_2023_valid_votes_max_abs_diff":float(cross["diff_valid"].abs().max()),
}
(ROOT/"backtest_2023_baseline.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(result,ensure_ascii=False,indent=2))
