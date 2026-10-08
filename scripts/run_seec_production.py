#!/usr/bin/env python3
"""Production SEEC compositional-temporal posterior sampler."""
from __future__ import annotations
import argparse, json, hashlib
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from src.reproducibility_contract import ExecutionContract

CANONICAL_SEED = ExecutionContract.seed
MIN_DRAWS = ExecutionContract.min_mc_draws

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",default="artifacts/data/cis_historical_2004_2023.csv")
    ap.add_argument("--output",default="ci_evidence/seec_production.json")
    ap.add_argument("--draws",type=int,default=2500)
    ap.add_argument("--tune",type=int,default=3000)
    ap.add_argument("--chains",type=int,default=4)
    ap.add_argument("--seed",type=int,default=CANONICAL_SEED)
    args=ap.parse_args()
    if args.seed != CANONICAL_SEED:
        raise SystemExit(f"BLOCKED: seed {args.seed} does not match canonical seed {CANONICAL_SEED}")
    if args.chains != 4: raise SystemExit("BLOCKED: production posterior requires exactly chains=4")
    if args.draws*args.chains<10000: raise SystemExit("BLOCKED: total_draws<10000")
    try:
        import pandas as pd
        import pymc as pm
    except Exception as exc:
        raise SystemExit(f"BLOCKED: PyMC production dependency unavailable: {exc}")
    input_path=Path(args.input)
    if not input_path.is_file():
        raise SystemExit(f"BLOCKED: SEEC input file not found: {input_path}")
    input_sha256=hashlib.sha256(input_path.read_bytes()).hexdigest()
    df=pd.read_csv(input_path)
    recent=Path("artifacts/data/cis_recent_2024_2026.csv")
    recent_sha256=None
    if recent.is_file():
        recent_sha256=hashlib.sha256(recent.read_bytes()).hexdigest()
        extra=pd.read_csv(recent)
        df=pd.concat([df,extra],ignore_index=True)
    script_sha256=hashlib.sha256(Path(__file__).resolve().read_bytes()).hexdigest()
    contract_path=Path(__file__).resolve().parents[1]/"src"/"reproducibility_contract.py"
    contract_sha256=hashlib.sha256(contract_path.read_bytes()).hexdigest()
    required={"study_id","study_date","party","cis_estimate_pct"}
    missing=required-set(df.columns)
    if missing: raise SystemExit(f"BLOCKED: missing columns: {sorted(missing)}")
    df=df.dropna(subset=["study_id","study_date","party","cis_estimate_pct"]).copy()
    df["study_id"]=df["study_id"].astype(str).str.strip()
    df["party"]=df["party"].astype(str).str.strip()
    df["study_date"]=pd.to_datetime(df["study_date"],errors="coerce",utc=True)
    if df["study_date"].isna().any():
        raise SystemExit("BLOCKED: invalid study_date values; temporal order cannot be trusted")
    if (df["study_id"]=="").any() or (df["party"]=="").any():
        raise SystemExit("BLOCKED: empty study_id or party label")
    df["cis_estimate_pct"]=pd.to_numeric(df["cis_estimate_pct"],errors="coerce")
    if df["cis_estimate_pct"].isna().any():
        raise SystemExit("BLOCKED: non-numeric CIS estimate")
    if (df["cis_estimate_pct"]<0).any():
        raise SystemExit("BLOCKED: negative CIS estimate")
    dates_per_study=df.groupby("study_id")["study_date"].nunique()
    if (dates_per_study!=1).any():
        bad=dates_per_study[dates_per_study!=1].index.astype(str).tolist()
        raise SystemExit(f"BLOCKED: study_id maps to multiple dates: {bad[:10]}")
    # The random walk must follow fieldwork chronology, never lexical study IDs.
    study_dates=df.groupby("study_id")["study_date"].min().sort_values(kind="stable")
    studies=study_dates.index.astype(str).tolist()
    # Random-walk variance scales with elapsed fieldwork time, not one equal
    # step per row: a 2-day gap must not equal a 2-year gap.
    day_values=study_dates.astype("int64").to_numpy(dtype=np.float64)/86_400_000_000_000.0
    positive_gaps=np.diff(day_values)
    if len(positive_gaps) and np.any(positive_gaps<=0):
        raise SystemExit("BLOCKED: field dates are not strictly increasing after study grouping")
    median_gap=float(np.median(positive_gaps)) if len(positive_gaps) else 1.0
    if not np.isfinite(median_gap) or median_gap<=0:
        raise SystemExit("BLOCKED: invalid median field-date interval")
    elapsed_days=np.diff(np.concatenate(([day_values[0]-median_gap],day_values)))
    temporal_scale=np.sqrt(elapsed_days/median_gap).astype(np.float64)
    if not np.isfinite(temporal_scale).all() or np.any(temporal_scale<=0):
        raise SystemExit("BLOCKED: invalid temporal innovation scale")
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
        innovations=pm.Deterministic("innovations",innovation_z*sigma*temporal_scale[:,None],dims=("study","party_minus_one"))
        eta=pm.Deterministic("eta",eta0[None,:]+pm.math.cumsum(innovations,axis=0),dims=("study","party_minus_one"))
        logits=pm.math.concatenate([eta,pm.math.zeros((len(studies),1))],axis=1)
        support=pm.Deterministic("support",pm.math.softmax(logits,axis=1),dims=("study","party"))
        log_concentration=pm.Normal("log_concentration",mu=float(np.log(50.0)),sigma=1.0)
        concentration=pm.Deterministic("concentration",pm.math.exp(log_concentration))
        pm.Dirichlet("observed_composition",a=support*concentration+1e-6,observed=y,dims=("study","party"))
        idata=pm.sample(draws=args.draws,tune=args.tune,chains=args.chains,cores=min(args.chains,4),random_seed=[args.seed+i for i in range(args.chains)],target_accept=0.995,max_treedepth=15,init="jitter+adapt_diag",jitter_max_retries=20,progressbar=False,return_inferencedata=True)
    posterior=idata.posterior
    total_draws=int(posterior.sizes["chain"]*posterior.sizes["draw"])
    if total_draws<MIN_DRAWS: raise SystemExit(f"BLOCKED: posterior has only {total_draws} draws")
    vals=np.asarray(posterior["support"].values)
    if not np.isfinite(vals).all(): raise SystemExit("BLOCKED: posterior contains non-finite values")
    div=int(np.asarray(idata.sample_stats["diverging"]).sum()) if "diverging" in idata.sample_stats else 0
    if div: raise SystemExit(f"BLOCKED: posterior contains {div} divergent transitions")
    try:
        import arviz as az
        # Diagnose the latent temporal trajectory too; hyperparameter-only
        # diagnostics can hide non-converged party-by-study states.
        summ=az.summary(idata,var_names=["temporal_sigma","log_concentration","eta0","eta"],round_to=None)
        rhat_max=float(np.nanmax(summ["r_hat"].to_numpy()))
        if not np.isfinite(rhat_max) or rhat_max>1.01: pass
    except ImportError: raise SystemExit("BLOCKED: ArviZ required for production diagnostics")
    ess_bulk_min=float(np.nanmin(summ["ess_bulk"].to_numpy()))
    ess_tail_min=float(np.nanmin(summ["ess_tail"].to_numpy()))
    # Match the master certification contract: ESS below 1000 is not production-certified.
    convergence_passed=bool(np.isfinite(rhat_max) and rhat_max<=1.01 and np.isfinite(ess_bulk_min) and ess_bulk_min>=1000 and np.isfinite(ess_tail_min) and ess_tail_min>=1000 and div==0)
    if not convergence_passed:
        raise SystemExit(f"BLOCKED: convergence diagnostics failed (r_hat={rhat_max!r}, ess_bulk_min={ess_bulk_min!r}, ess_tail_min={ess_tail_min!r}, divergences={div})")
    out={
        "schema":"SEEC_PRODUCTION_POSTERIOR_V2",
        "status":"PASS",
        "model":"hierarchical_compositional_temporal_dirichlet_logistic_normal",
        "temporal_time_scale":"sqrt(elapsed_days / median_positive_field_date_gap_days)",
        "median_positive_field_date_gap_days":median_gap,
        "input":str(input_path),
        "input_sha256":input_sha256,
        "supplemental_input":str(recent) if recent.is_file() else None,
        "supplemental_input_sha256":recent_sha256,
        "script_sha256":script_sha256,
        "reproducibility_contract_sha256":contract_sha256,
        "studies":len(studies),
        "parties":len(parties),
        "chains":args.chains,
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
