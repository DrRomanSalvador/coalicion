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

def party_family(label: str) -> str:
    """Stable national/coalition family used only for historical seat calibration."""
    s = re.sub(r"[^A-Z0-9ÁÉÍÓÚÜÑ ]+", " ", str(label).upper()).strip()
    if "PSOE" in s or s == "PSC" or "PSC " in s:
        return "PSOE"
    if s == "PP" or s.startswith("PP "):
        return "PP"
    if "VOX" in s:
        return "VOX"
    if any(token in s for token in (
        "SUMAR", "PODEMOS", "UNIDAS PODEMOS", "IZQUIERDA UNIDA",
        "IU ", "IU", "MÁS PAÍS", "MAS PAIS", "COMPROMÍS", "COMPROMIS",
        "EN COMÚ", "EN COMU", "COMUNS", "ECP",
    )):
        return "SUMAR"
    return str(label).strip()

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

def lottery_tie_breaker(prov: str):
    def choose(tied):
        key="|".join((str(SEED),prov,*sorted(tied))).encode("utf-8")
        digest=hashlib.sha256(key).digest()
        return sorted(tied)[digest[0] % len(tied)]
    return choose

# Actual 2023 seats are deterministically reconstructed from primary
# official votes with the canonical electoral engine. This avoids relying on
# an unpopulated seat column while preserving the legal allocation contract.
actual_seats={}
for prov,votes in target_maps.items():
    seat_n=int(seats.loc[seats["prov"].eq(prov),"escanos_2023"].iloc[0])
    valid=int(target_valid[prov])
    alloc=allocate({p:int(v) for p,v in votes.items()},seat_n,valid,
                   special=prov if prov in {"Ceuta","Melilla"} else "",
                   blank_votes=int(target_blank.get(prov,0)),
                   tie_breaker=lottery_tie_breaker(prov))
    if alloc.status!="OK":
        raise RuntimeError(f"actual 2023 allocation blocked: {prov} {alloc.status} {alloc.tie}")
    for party,s in alloc.seats.items():
        actual_seats[party]=actual_seats.get(party,0)+int(s)
if sum(actual_seats.values()) != 350:
    raise SystemExit(f"reconstructed official 2023 seats do not sum to 350: {sum(actual_seats.values())}")

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

# Predictive Monte Carlo dispersion is calibrated only from pre-2023
# territorial vote-share transitions. This removes the counts+1 overconfidence.
def historical_predictive_parameters():
    squared_changes = []
    entry_shares = []
    dates = sorted(d for d in df["fecha_eleccion"].astype(str).str[:10].unique()
                   if d < "2023-07-23")
    for previous_date, current_date in zip(dates, dates[1:]):
        prev_p, prev_valid, prev_blank, _ = election_matrix_by_date(previous_date)
        curr_p, curr_valid, curr_blank, _ = election_matrix_by_date(current_date)
        prev_maps = {p: dict(zip(g["party"], g["votos"])) for p,g in prev_p.groupby("prov")}
        curr_maps = {p: dict(zip(g["party"], g["votos"])) for p,g in curr_p.groupby("prov")}
        for prov in sorted(set(prev_maps) & set(curr_maps)):
            pt=max(int(prev_valid[prov])-int(prev_blank.get(prov,0)),1)
            ct=max(int(curr_valid[prov])-int(curr_blank.get(prov,0)),1)
            for party in set(prev_maps[prov]) | set(curr_maps[prov]):
                p0=int(prev_maps[prov].get(party,0))/pt
                p1=int(curr_maps[prov].get(party,0))/ct
                if p0 > 0:
                    squared_changes.append((p1-p0)**2)
                elif p1 > 0:
                    entry_shares.append(p1)
    if len(squared_changes) < 100:
        raise RuntimeError("insufficient historical vote-share changes for MC calibration")
    # Pooled method-of-moments Dirichlet concentration:
    # Var(p_i)=p_i(1-p_i)/(K+1).
    prior_scale=[]
    for previous_date, current_date in zip(dates, dates[1:]):
        prev_p, prev_valid, prev_blank, _ = election_matrix_by_date(previous_date)
        prev_maps={p:dict(zip(g["party"],g["votos"])) for p,g in prev_p.groupby("prov")}
        for prov, pm in prev_maps.items():
            total=max(int(prev_valid[prov])-int(prev_blank.get(prov,0)),1)
            for v in pm.values():
                p0=int(v)/total
                if p0 > 0:
                    prior_scale.append(p0*(1-p0))
    k_raw=float(np.mean(prior_scale))/max(float(np.mean(squared_changes)),1e-12)-1.0
    concentration=float(np.clip(k_raw,2.0,500.0))
    entry_share=float(np.clip(np.median(entry_shares) if entry_shares else 0.002,0.0005,0.05))
    return concentration, entry_share

PREDICTIVE_CONCENTRATION, ENTRY_SHARE = historical_predictive_parameters()

rng=np.random.Generator(np.random.PCG64(SEED))
sim_seats={p:np.zeros(N_SIM,dtype=np.int16) for p in parties}
target_only=sorted(set(parties)-set().union(*[set(v) for v in train_maps.values()]))
for prov in sorted(train_maps):
    votes=train_maps[prov]
    valid=int(train_valid[prov])
    blank=int(train_blank.get(prov,0))
    party_total=valid-blank
    seat_n=int(seats.loc[seats["prov"].eq(prov),"escanos_2023"].iloc[0])
    ps=sorted(set(votes)|set(parties))
    prior_total=max(party_total,1)
    prior_shares={p:int(votes.get(p,0))/prior_total for p in ps}
    alpha=np.array([
        max(PREDICTIVE_CONCENTRATION*prior_shares[p],0.0)
        +(PREDICTIVE_CONCENTRATION*ENTRY_SHARE if p in target_only else 0.0)
        +0.05 for p in ps
    ],dtype=float)
    draws=rng.dirichlet(alpha,size=N_SIM)
    for i in range(N_SIM):
        dv={p:int(round(x*party_total)) for p,x in zip(ps,draws[i])}
        residual=party_total-sum(dv.values())
        if residual:
            winner=max(dv,key=dv.get)
            dv[winner]+=residual
        alloc=allocate({p:int(v) for p,v in dv.items()},seat_n,valid,
                       special=prov if prov in {"Ceuta","Melilla"} else "",
                       blank_votes=blank,tie_breaker=lottery_tie_breaker(prov))
        if alloc.status!="OK":
            raise RuntimeError(f"simulated allocation blocked: {prov} {alloc.status} {alloc.tie}")
        for p,s in alloc.seats.items():
            if p in sim_seats: sim_seats[p][i]+=s

medians=np.array([float(np.median(sim_seats[p])) for p in parties])
actual_vec=np.array([actual_seats.get(p,0) for p in parties],dtype=float)
seat_mae=float(np.mean(np.abs(actual_vec-medians)))
seat_rmse=float(np.sqrt(np.mean((actual_vec-medians)**2)))

# Historical conformal calibration of territorial seat uncertainty.
# Calibration uses only election pairs strictly before 2023. For each pair,
# the predictor is persistence from the previous election and the target is
# the current election. 2023 is never used to fit the calibration quantile.
#
# The historical official file is the sole source for historical seat counts.
# If those counts are absent, calibration fails closed instead of inventing
# a seat structure.

def official_seat_structure(election_date: str):
    x = df[df["fecha_eleccion"].astype(str).str[:10].eq(election_date)].copy()
    grouped = x.groupby("prov")["escaños"].sum().astype(int).to_dict()
    positive = {p:s for p,s in grouped.items() if s > 0}
    if not positive:
        return None
    if sum(positive.values()) != 350:
        raise RuntimeError(
            f"historical seat structure invalid for {election_date}: "
            f"sum={sum(positive.values())}"
        )
    return positive

def actual_seats_from_official(election_date: str):
    x = df[df["fecha_eleccion"].astype(str).str[:10].eq(election_date)].copy()
    if x.empty:
        raise RuntimeError(f"missing election {election_date}")
    y = x[x["kind"].eq("PARTY")].copy()
    if y["escaños"].sum() <= 0:
        return None
    return y.groupby("party")["escaños"].sum().astype(int).to_dict()

def persistent_seats(previous_date: str, current_date: str, current_structure):
    prev_p, prev_valid, prev_blank, _ = election_matrix_by_date(previous_date)
    prev_maps = {p: dict(zip(g["party"], g["votos"])) for p,g in prev_p.groupby("prov")}
    pred = {}
    for prov, seat_n in current_structure.items():
        votes = prev_maps.get(prov, {})
        if not votes:
            continue
        valid = int(prev_valid[prov])
        blank = int(prev_blank.get(prov, 0))
        alloc = allocate(
            {p:int(v) for p,v in votes.items()},
            int(seat_n),
            valid,
            special=prov if prov in {"Ceuta","Melilla"} else "",
            blank_votes=blank,
            tie_breaker=lottery_tie_breaker(prov),
        )
        if alloc.status != "OK":
            raise RuntimeError(
                f"historical allocation blocked: {previous_date}->{current_date} "
                f"{prov} {alloc.status} {alloc.tie}"
            )
        for party, seats_n in alloc.seats.items():
            pred[party] = pred.get(party, 0) + int(seats_n)
    return pred

historical_dates = sorted(
    d for d in df["fecha_eleccion"].astype(str).str[:10].unique()
    if d < "2023-07-23"
)
historical_residuals = []
historical_new_party_residuals = []
historical_party_residuals = {}
historical_family_residuals = []
historical_new_family_residuals = []
historical_family_residuals_by_name = {}
historical_pair_count = 0

for previous_date, current_date in zip(historical_dates, historical_dates[1:]):
    structure = official_seat_structure(current_date)
    actual = actual_seats_from_official(current_date)
    if structure is None or actual is None:
        continue
    predicted = persistent_seats(previous_date, current_date, structure)
    historical_pair_count += 1
    all_parties = set(predicted) | set(actual)
    for party in all_parties:
        pv = int(predicted.get(party, 0))
        av = int(actual.get(party, 0))
        residual = abs(av - pv)
        historical_residuals.append(residual)
        historical_party_residuals.setdefault(party, []).append(residual)
        if pv == 0 and av > 0:
            historical_new_party_residuals.append(residual)

    predicted_family = {}
    actual_family = {}
    for party, seats_n in predicted.items():
        family = party_family(party)
        predicted_family[family] = predicted_family.get(family, 0) + int(seats_n)
    for party, seats_n in actual.items():
        family = party_family(party)
        actual_family[family] = actual_family.get(family, 0) + int(seats_n)
    for family in set(predicted_family) | set(actual_family):
        pv = int(predicted_family.get(family, 0))
        av = int(actual_family.get(family, 0))
        residual = abs(av - pv)
        historical_family_residuals.append(residual)
        historical_family_residuals_by_name.setdefault(family, []).append(residual)
        if pv == 0 and av > 0:
            historical_new_family_residuals.append(residual)

if historical_pair_count < 2 or len(historical_residuals) < 20:
    raise RuntimeError(
        "insufficient pre-2023 historical seat residuals for conformal calibration"
    )

def conformal_quantile(values, coverage=0.90):
    vals = np.sort(np.asarray(values, dtype=float))
    if vals.size == 0:
        raise RuntimeError("empty conformal calibration set")
    # Finite-sample split-conformal quantile:
    # ceil((n+1)*coverage) / n, capped at the last observed residual.
    rank = int(np.ceil((len(vals) + 1) * coverage)) - 1
    rank = min(max(rank, 0), len(vals) - 1)
    return float(vals[rank])

Q90_SEATS = conformal_quantile(historical_residuals, 0.90)
Q90_NEW_PARTY_SEATS = (
    conformal_quantile(historical_new_party_residuals, 0.90)
    if historical_new_party_residuals
    else Q90_SEATS
)
if len(historical_family_residuals) < 20:
    raise RuntimeError("insufficient family-level seat residuals for calibration")
Q90_FAMILY_SEATS = conformal_quantile(historical_family_residuals, 0.90)
Q90_NEW_FAMILY_SEATS = (
    conformal_quantile(historical_new_family_residuals, 0.90)
    if historical_new_family_residuals
    else Q90_FAMILY_SEATS
)

def family_q90(family: str, predicted: int) -> tuple[float, str, int]:
    vals = historical_family_residuals_by_name.get(family, [])
    if len(vals) >= 3:
        return conformal_quantile(vals, 0.90), "FAMILY", len(vals)
    if predicted == 0 and historical_new_family_residuals:
        return Q90_NEW_FAMILY_SEATS, "NEW_FAMILY", len(historical_new_family_residuals)
    return Q90_FAMILY_SEATS, "GLOBAL_FAMILY_FALLBACK", len(historical_family_residuals)

# Party-specific finite-sample conformal calibration.
Q90_PARTY = {}
for party in parties:
    obs = historical_party_residuals.get(party, [])
    if len(obs) >= 3:
        Q90_PARTY[party] = conformal_quantile(obs, 0.90)
    else:
        family = party_family(party)
        family_values = []
        for previous_date, current_date in zip(historical_dates, historical_dates[1:]):
            structure = official_seat_structure(current_date)
            actual_hist = actual_seats_from_official(current_date)
            if structure is None or actual_hist is None:
                continue
            predicted_hist = persistent_seats(previous_date, current_date, structure)
            pf, af = {}, {}
            for p, s in predicted_hist.items():
                f = party_family(p); pf[f] = pf.get(f, 0) + int(s)
            for p, s in actual_hist.items():
                f = party_family(p); af[f] = af.get(f, 0) + int(s)
            family_values.append(abs(int(af.get(family, 0)) - int(pf.get(family, 0))))
        fallback = family_values if len(family_values) >= 3 else historical_new_party_residuals
        Q90_PARTY[party] = conformal_quantile(fallback, 0.90)


# Persistence point prediction for 2023. The conformal interval is calibrated
# independently from this target election and then applied to every 2023 party.
point_pred_2023 = {}
for prov, votes in train_maps.items():
    seat_n = int(seats.loc[seats["prov"].eq(prov), "escanos_2023"].iloc[0])
    valid = int(train_valid[prov])
    blank = int(train_blank.get(prov, 0))
    alloc = allocate(
        {p:int(v) for p,v in votes.items()},
        seat_n,
        valid,
        special=prov if prov in {"Ceuta","Melilla"} else "",
        blank_votes=blank,
        tie_breaker=lottery_tie_breaker(prov),
    )
    if alloc.status != "OK":
        raise RuntimeError(
            f"2023 point prediction blocked: {prov} {alloc.status} {alloc.tie}"
        )
    for party, seats_n in alloc.seats.items():
        point_pred_2023[party] = point_pred_2023.get(party, 0) + int(seats_n)

actual_family_seats = {}
predicted_family_seats = {}
for party, seats_n in actual_seats.items():
    family = party_family(party)
    actual_family_seats[family] = actual_family_seats.get(family, 0) + int(seats_n)
for party, seats_n in point_pred_2023.items():
    family = party_family(party)
    predicted_family_seats[family] = predicted_family_seats.get(family, 0) + int(seats_n)

intervals={}
winners=[p for p,s in actual_seats.items() if s>0]
covered=0
for party in winners:
    predicted = int(point_pred_2023.get(party, 0))
    if predicted == 0:
        q = Q90_NEW_FAMILY_SEATS
        method = "split_conformal_absolute_emergent_family_seat_residual"
    else:
        q = Q90_PARTY.get(party, Q90_SEATS)
        method = "split_conformal_absolute_party_or_family_seat_residual"
    lo = max(0.0, predicted - q)
    hi = min(350.0, predicted + q)
    intervals[party]={
        "actual": int(actual_seats[party]),
        "p10": float(lo),
        "p50": float(predicted),
        "p90": float(hi),
        "interval_method": method,
        "calibration_q90": float(q),
    }
    covered += int(lo <= actual_seats[party] <= hi)

coverage=covered/len(winners) if winners else float("nan")

result={
 "election":"2023",
 "cutoff":"2019-11-10",
 "model":"baseline_persistence_2019N_with_historical_conformal_seat_calibration",
 "note":"Canonical official Interior results. The prediction uses only 2019N votes. Seat uncertainty is calibrated from pre-2023 historical persistence errors; emerging-party intervals use the pre-2023 distribution of positive-seat parties absent from the preceding election.",
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
   "coverage_actual_seats_in_mc_p10_p90_winners":float(np.mean([
       np.percentile(sim_seats[p],[10])[0] <= actual_seats[p] <=
       np.percentile(sim_seats[p],[90])[0] for p in winners
   ])) if winners else float("nan"),
   "coverage_actual_seats_in_calibrated_p10_p90_winners":coverage,
   "coverage_unit":"NATIONAL_PARTY",
   "party_specific_q90_count":sum(1 for p in winners if len(historical_party_residuals.get(p, [])) >= 3),
   "n_2023_seat_winning_families":len(winners),
   "n_2023_seat_winning_parties":len(winners),
   "historical_conformal_pairs":historical_pair_count,
   "historical_conformal_residuals":len(historical_residuals),
   "historical_new_party_residuals":len(historical_new_party_residuals),
   "historical_family_residuals":len(historical_family_residuals),
   "historical_new_family_residuals":len(historical_new_family_residuals),
   "conformal_q90_family_seats":Q90_FAMILY_SEATS,
   "conformal_q90_new_family_seats":Q90_NEW_FAMILY_SEATS,
   "family_specific_calibrations": {
       family: {"n": len(vals), "q90": conformal_quantile(vals, 0.90)}
       for family, vals in sorted(historical_family_residuals_by_name.items())
       if len(vals) >= 3
   },
   "conformal_nominal_coverage":0.90,
   "conformal_q90_seats":Q90_SEATS,
   "conformal_q90_new_party_seats":Q90_NEW_PARTY_SEATS
 },
 "seat_intervals":intervals,
 "contracts":{
   "official_source":True,
   "seat_sum_350":True,
   "no_future_vote_input":True,
   "canonical_electoral_engine":True,
   "absolute_ties_reproducible_lottery":True,
   "historical_conformal_calibration":True,
   "calibration_before_target_election":True,
   "new_party_uncertainty_calibrated":True,
   "family_level_calibration":True,
   "party_specific_calibration":True,
   "calibrated_coverage_gate": bool(coverage >= 0.85)
 }
}
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(result,ensure_ascii=False,indent=2))
