#!/usr/bin/env python3
"""Execute the actual SEEC Bayesian model on materialized primary evidence.

The 2023 CIS pre-election estimate is a published complete composition whose
shares sum to 100% after display rounding. It is used only as survey evidence.
The official Interior 2023 constituency results provide the historical
territorial likelihood. No poll value is inferred or normalized.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import pymc as pm
import arviz as az

from src.seec_bayesian import SurveyRow, ProvinceObservation, build_model
from src.cis_history import load as load_cis


RESULTS = Path("data/resultados_oficiales_2004_2023.csv")
OUTPUT = Path("ci_evidence/seec_posterior.json")
SEED = 20261006
DRAWS_PER_CHAIN = 5000
CHAINS = 2

CIS_STUDY_ID = "3411"
CIS_SAMPLE_SIZE = 29201
OTHER_PARTY = "OTHER_UNSPECIFIED"

ALIASES = {
    "pp":"PP","partido popular":"PP",
    "psoe":"PSOE","partido socialista obrero español":"PSOE",
    "sumar":"SUMAR","movimiento sumar":"SUMAR",
    "vox":"VOX","erc":"ERC","esquerra republicana de catalunya":"ERC",
    "eh-bildu":"EH_BILDU","eh bildu":"EH_BILDU","bildu":"EH_BILDU",
    "juntsxcat":"JUNTS","junts per catalunya":"JUNTS","junts":"JUNTS",
    "eaj-pnv":"PNV","pnv":"PNV","bng":"BNG",
    "cca":"CC","coalición canaria":"CC","cc":"CC",
    "cup":"CUP","teruel existe":"TERUEL_EXISTE",
    "en blanco":"EN_BLANCO","votos en blanco":"EN_BLANCO",
}
CIS_CANONICAL = [r for r in load_cis() if r.election == "2023" and r.study_id == CIS_STUDY_ID]
SURVEY = {r.party: r.cis_estimate_pct for r in CIS_CANONICAL}
SURVEY_SOURCE_SUM = sum(SURVEY.values())

def norm(s):
    return ALIASES.get(" ".join(str(s).lower().replace("_"," ").split()),
                       " ".join(str(s).lower().replace("_"," ").split()))

def sha256(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()

def load_historical(parties):
    rows=[]
    with RESULTS.open(encoding="utf-8",newline="") as f:
        for r in csv.DictReader(f):
            if r["election"] == "2023J":
                rows.append(r)
    provinces=sorted({r["circunscripcion"] for r in rows})
    if len(provinces) != 52:
        raise RuntimeError(f"expected 52 constituencies, got {len(provinces)}")
    observations=[]
    for province in provinces:
        for party in parties:
            votes=0
            for r in rows:
                if r["circunscripcion"] != province: continue
                p=norm(r["partido"])
                v=int(float(r["votos"]))
                if p == party:
                    votes += v
                elif party == OTHER_PARTY and p not in parties and "nulo" not in p and "total" not in p:
                    votes += v
            observations.append(ProvinceObservation(
                election="2023J", province=province, party=party,
                votes=votes, valid_votes=max(1,sum(
                    int(float(r["votos"])) for r in rows
                    if r["circunscripcion"]==province and "nulo" not in norm(r["partido"]) and "total" not in norm(r["partido"])
                )), turnout=0.0))
    return provinces, observations

def main():
    cis_rows = [r for r in load_cis() if r.election == "2023" and r.study_id == CIS_STUDY_ID]
    if not cis_rows:
        raise RuntimeError("canonical CIS dataset missing study 3411/2023")
    survey = {r.party: r.cis_estimate_pct for r in cis_rows}
    source_sum = sum(survey.values())
    if not 0 < source_sum < 100:
        raise RuntimeError(f"invalid canonical CIS composition sum: {source_sum}")
    survey[OTHER_PARTY] = 100.0 - source_sum
    parties = tuple(survey)
    field_dates = {r.study_date for r in cis_rows}
    if len(field_dates) != 1:
        raise RuntimeError("canonical CIS study has inconsistent study dates")
    field_date = next(iter(field_dates))
    if not RESULTS.is_file():
        raise RuntimeError("primary historical results are not materialized")
    provinces, historical = load_historical(parties)
    surveys=[]
    for party, share in survey.items():
        surveys.append(SurveyRow(
            poll_id="CIS-3411-2023",
            field_date=field_date,
            house="CIS",
            party=party,
            estimate=share/100.0,
            sample_size=CIS_SAMPLE_SIZE,
        ))
    model=build_model(provinces, parties, historical, surveys)
    with model:
        idata=pm.sample(
            draws=DRAWS_PER_CHAIN,
            tune=500,
            chains=CHAINS,
            cores=2,
            target_accept=0.9,
            random_seed=SEED,
            progressbar=False,
            compute_convergence_checks=True,
        )
    total_draws=int(idata.posterior.sizes["chain"]*idata.posterior.sizes["draw"])
    rhat = az.rhat(idata)
    rhat_values = np.asarray(rhat.to_array().values, dtype=float)
    rhat_max = float(np.nanmax(rhat_values))
    if not np.isfinite(rhat_max):
        raise RuntimeError("SEEC convergence evidence is non-finite")
    if rhat_max > 1.01:
        raise RuntimeError(f"SEEC convergence gate failed: max_rhat={rhat_max:.6f}")
    result={
        "schema":"SEEC_PRODUCTION_EXECUTION_V1",
        "status":"PASS",
        "execution_verified": True,
        "methodology":"REINA-SEEC 4.0",
        "model":"src.seec_bayesian.build_model",
        "survey_source":"canonical CIS historical dataset / study 3411",
        "survey_publication":"2023-07-05",
        "survey_field_end":"2023-06-27",
        "survey_sample_size":CIS_SAMPLE_SIZE,
        "survey_composition_source_sum":source_sum,
        "survey_composition_sum":100.0,
        "survey_residual_category":OTHER_PARTY,
        "historical_source":"Ministerio del Interior",
        "historical_election":"2023-07-23",
        "constituencies":len(provinces),
        "draws_per_chain":DRAWS_PER_CHAIN,
        "chains":CHAINS,
        "draws":total_draws,
        "total_posterior_draws":total_draws,
        "seed":SEED,
        "rng":"numpy.PCG64",
        "input_sha256":sha256(RESULTS),
        "convergence": {"max_rhat": rhat_max, "threshold": 1.01, "status": "PASS"},
        "external_audit":False,
        "note":"Execution evidence only; this does not certify predictive accuracy or external independence."
    }
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
