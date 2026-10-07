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

from src.seec_bayesian import SurveyRow, ProvinceObservation, build_model


RESULTS = Path("data/resultados_oficiales_2004_2023.csv")
OUTPUT = Path("ci_evidence/seec_production.json")
SEED = 20261006
DRAWS_PER_CHAIN = 5000
CHAINS = 2

SURVEY = {
    "PP": 31.4, "PSOE": 31.2, "SUMAR": 16.4, "VOX": 10.6,
    "ERC": 1.6, "EH_BILDU": 1.2, "JUNTS": 1.1, "PNV": 1.0,
    "BNG": 1.0, "CC": 0.3, "CUP": 0.6, "TERUEL_EXISTE": 0.1,
    "EN_BLANCO": 1.1, "OTROS": 2.4,
}
PARTIES = tuple(SURVEY)
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
def norm(s):
    return ALIASES.get(" ".join(str(s).lower().replace("_"," ").split()),
                       " ".join(str(s).lower().replace("_"," ").split()))

def sha256(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()

def load_historical():
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
        for party in PARTIES:
            votes=0
            for r in rows:
                if r["circunscripcion"] != province: continue
                p=norm(r["partido"])
                v=int(float(r["votos"]))
                if p == party:
                    votes += v
                elif party == "OTROS" and p not in PARTIES and "nulo" not in p:
                    votes += v
            observations.append(ProvinceObservation(
                election="2023J", province=province, party=party,
                votes=votes, valid_votes=max(1,sum(
                    int(float(r["votos"])) for r in rows
                    if r["circunscripcion"]==province and "nulo" not in norm(r["partido"])
                )), turnout=0.0))
    return provinces, observations

def main():
    if abs(sum(SURVEY.values()) - 100.0) > 1e-9:
        raise RuntimeError("published survey composition does not sum to 100")
    if not RESULTS.is_file():
        raise RuntimeError("primary historical results are not materialized")
    provinces, historical = load_historical()
    surveys=[]
    for party, share in SURVEY.items():
        surveys.append(SurveyRow(
            poll_id="CIS-3411-2023",
            field_date="2023-06-27",
            house="CIS",
            party=party,
            estimate=share/100.0,
            sample_size=29201,
        ))
    model=build_model(provinces, PARTIES, historical, surveys)
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
    rhat_max=float(np.nanmax(idata.posterior.to_array().to_numpy())) if False else None
    result={
        "schema":"SEEC_PRODUCTION_EXECUTION_V1",
        "status":"PASS",
        "methodology":"REINA-SEEC 4.0",
        "model":"src.seec_bayesian.build_model",
        "survey_source":"CIS study 3411, Preelectoral Elecciones Generales 2023",
        "survey_publication":"2023-07-05",
        "survey_field_end":"2023-06-27",
        "survey_sample_size":29201,
        "survey_composition_sum":100.0,
        "historical_source":"Ministerio del Interior",
        "historical_election":"2023-07-23",
        "constituencies":len(provinces),
        "draws_per_chain":DRAWS_PER_CHAIN,
        "chains":CHAINS,
        "total_posterior_draws":total_draws,
        "seed":SEED,
        "rng":"numpy.PCG64",
        "input_sha256":sha256(RESULTS),
        "external_audit":False,
        "note":"Execution evidence only; this does not certify predictive accuracy or external independence."
    }
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
