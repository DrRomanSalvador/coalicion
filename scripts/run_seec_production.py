#!/usr/bin/env python3
"""Production SEEC compositional-temporal posterior sampler."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
from src.reproducibility_contract import ExecutionContract

CANONICAL_SEED = ExecutionContract.seed
MIN_DRAWS = ExecutionContract.min_mc_draws

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",default="artifacts/data/cis_historical_2004_2023.csv")
    ap.add_argument("--output",default="ci_evidence/seec_production.json")
    ap.add_argument("--draws",type=int,default=5000)
    ap.add_argument("--tune",type=int,default=1500)
    ap.add_argument("--seed",type=int,default=CANONICAL_SEED)
    args=ap.parse_args()
    if args.seed != CANONICAL_SEED:
        raise SystemExit(f"BLOCKED: seed {args.seed} does not match canonical seed {CANONICAL_SEED}")
    if args.draws*4<MIN_DRAWS: raise SystemExit(f"BLOCKED: four-chain posterior requires >= {MIN_DRAWS} total draws")
    try:
        import pandas as pd
        import pymc as pm
    except Exception as exc:
        raise SystemExit(f"BLOCKED: PyMC production dependency unavailable: {exc}")
    df=pd.read_csv(args.input)
    recent=Path("artifacts/data/cis_recent_2024_2026.csv")
    if recent.is_file():
        extra=pd.read_csv(recent)
        df=pd.concat([df,extra],ignore_index=True)
    required={"study_id","study_date","party","cis_estimate_pct"}
    missing=required-set(df.columns)
    if missing: raise SystemExit(f"BLOCKED: missing columns: {sorted(missing)}")
    df=df.dropna(subset=["study_id","study_date","party","cis_estimate_pct"]).copy()
    df["cis_estimate_pct"]=pd.to_numeric(df["cis_estimate_pct"],errors="coerce")
    df=df[df["cis_estimate_pct"]>=0]
    studies=sorted(df["study_id"].astype(str).unique())
    parties=sorted(df["party"].astype(str).unique())
    if len(studies)<12 or len(parties)<12: raise SystemExit("BLOCKED: SEEC requires >=12 studies and >=12 parties")
    mat=np.zeros((len(studies),len(parties)))
    si={s:i for i,s in enumerate(studies)}; pi={p:i for i,p in enumerate(parties)}
    for r in df.itertuples(index=False): mat[si[str(r.study_id)],pi[str(r.party)]]+=float(r.cis_estimate_pct)
    row_sums=mat.sum(axis=1)
    if np.any(row_sums<=0): raise SystemExit("BLOCKED: study with non-positive composition")
    y=np.clip(mat/row_sums[:,None],1e-6,1.0); y=y/y.sum(axis=1,keepdims=True)
    coords={"study":studies,"party":parties,"party_minus_one":parties[:-1]}
    with pm.Model(coords=coords) as model:
        sigma=pm.HalfNormal("temporal_sigma",sigma=0.25)
        eta0=pm.Normal("eta0",mu=0.0,sigma=2.0,dims="party_minus_one")
        innovation_z=pm.Normal("innovation_z",0.0,1.0,dims=("study","party_minus_one"))
        innovations=pm.Deterministic("innovations",innovation_z*sigma,dims=("study","party_minus_one"))
        eta=pm.Deterministic("eta",eta0[None,:]+pm.math.cumsum(innovations,axis=0),dims=("study","party_minus_one"))
        logits=pm.math.concatenate([eta,pm.math.zeros((len(studies),1))],axis=1)
        support=pm.Deterministic("support",pm.math.softmax(logits,axis=1),dims=("study","party"))
        log_concentration=pm.Normal("log_concentration",mu=float(np.log(50.0)),sigma=1.0)
        concentration=pm.Deterministic("concentration",pm.math.exp(log_concentration))
        pm.Dirichlet("observed_composition",a=support*concentration+1e-6,observed=y,dims=("study","party"))
        idata=pm.sample(draws=args.draws,tune=args.tune,chains=4,cores=4,random_seed=[args.seed,args.seed+1,args.seed+2,args.seed+3],target_accept=0.995,max_treedepth=15,init="jitter+adapt_diag",jitter_max_retries=20,progressbar=False,return_inferencedata=True)
    posterior=idata.posterior
    total_draws=int(posterior.sizes["chain"]*posterior.sizes["draw"])
    if total_draws<MIN_DRAWS: raise SystemExit(f"BLOCKED: posterior has only {total_draws} draws")
    vals=np.asarray(posterior["support"].values)
    if not np.isfinite(vals).all(): raise SystemExit("BLOCKED: posterior contains non-finite values")
    div=int(np.asarray(idata.sample_stats["diverging"]).sum()) if "diverging" in idata.sample_stats else 0
    if div: raise SystemExit(f"BLOCKED: posterior contains {div} divergent transitions")
    try:
        import arviz as az
        summ=az.summary(idata,var_names=["temporal_sigma","log_concentration","concentration"],round_to=None)
        rhat_max=float(np.nanmax(summ["r_hat"].to_numpy()))
        if not np.isfinite(rhat_max) or rhat_max>1.01: pass
    except ImportError: raise SystemExit("BLOCKED: ArviZ required for production diagnostics")
    ess_bulk_min=float(np.nanmin(summ["ess_bulk"].to_numpy()))
    ess_tail_min=float(np.nanmin(summ["ess_tail"].to_numpy()))
    convergence_passed=bool(np.isfinite(rhat_max) and rhat_max<=1.01 and np.isfinite(ess_bulk_min) and ess_bulk_min>=400 and np.isfinite(ess_tail_min) and ess_tail_min>=400 and div==0)
    if not convergence_passed:
        raise SystemExit(f"BLOCKED: convergence diagnostics failed (r_hat={rhat_max!r}, ess_bulk_min={ess_bulk_min!r}, ess_tail_min={ess_tail_min!r}, divergences={div})")
    out={
        "schema":"SEEC_PRODUCTION_POSTERIOR_V2",
        "status":"PASS",
        "model":"hierarchical_compositional_temporal_dirichlet_logistic_normal",
        "input":args.input,
        "supplemental_input":"artifacts/data/cis_recent_2024_2026.csv" if recent.is_file() else None,
        "studies":len(studies),
        "parties":len(parties),
        "chains":4,
        "draws_per_chain":args.draws,
        "total_draws":total_draws,
        "tune_per_chain":args.tune,
        "seed":args.seed,
        "canonical_seed":CANONICAL_SEED,
        "posterior_mean_last_study":{p:float(vals[:,:,-1,i].mean()) for i,p in enumerate(parties)},
        "diagnostics":{"divergences":div,"max_r_hat":rhat_max,"min_ess_bulk":ess_bulk_min,"min_ess_tail":ess_tail_min},
        "convergence":{"passed":convergence_passed},
        "fail_closed":True,
        "note":"Posterior describes CIS compositional support; it is not itself an election-outcome posterior."
    }
    p=Path(args.output); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); print(json.dumps(out,ensure_ascii=False,indent=2))
if __name__=="__main__": main()
