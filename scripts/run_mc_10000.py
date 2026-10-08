#!/usr/bin/env python3
"""Independent 10,000-draw electoral Monte Carlo engine gate."""
from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.electoral import allocate
from src.reproducibility_contract import ExecutionContract

SOURCE=ROOT/"artifacts/data/election_2023_canonical.json"
OUT=ROOT/"ci_evidence/mc_10000.json"
SEED=ExecutionContract.seed
N_ITER=10000
CONCENTRATION=200.0

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--iterations",type=int,default=N_ITER)
    ap.add_argument("--seed",type=int,default=SEED)
    args=ap.parse_args()
    if args.seed != SEED:
        raise SystemExit(f"BLOCKED: seed {args.seed} does not match canonical seed {SEED}")
    if not SOURCE.is_file():
        raise SystemExit("BLOCKED: canonical 2023 matrix missing")
    data=json.loads(SOURCE.read_text(encoding="utf-8"))
    constituencies=((data.get("data") or {}).get("constituencies") or {})
    if len(constituencies)!=52:
        raise SystemExit("BLOCKED: canonical matrix must contain 52 constituencies")
    seats_total=sum(int(row.get("seats",0)) for row in constituencies.values())
    if seats_total!=350:
        raise SystemExit("BLOCKED: canonical matrix must contain 350 seats")
    n=int(args.iterations)
    if n<10000:
        raise SystemExit("BLOCKED: Monte Carlo requires at least 10,000 draws")
    rng=np.random.Generator(np.random.PCG64(int(args.seed)))
    seat_sums=np.empty(n,dtype=np.int16)
    status_counts={}
    for i in range(n):
        total_seats=0
        for name,row in constituencies.items():
            votes={str(p):int(v) for p,v in (row.get("parties") or {}).items()}
            blank=int(row.get("blank_votes",0))
            seat_n=int(row["seats"])
            total=max(sum(votes.values()),1)
            probs=np.array([v/total for v in votes.values()],dtype=float)
            draw=rng.dirichlet(np.maximum(probs*CONCENTRATION,0.05))
            simulated={party:int(round(float(frac)*total)) for party,frac in zip(votes,draw)}
            diff=total-sum(simulated.values())
            if diff:
                simulated[max(simulated,key=simulated.get)]+=diff
            valid=sum(simulated.values())+blank
            special=name if name in {"Ceuta","Melilla"} else ""
            allocation=allocate(simulated,seat_n,valid,special=special,blank_votes=blank)
            status_counts[allocation.status]=status_counts.get(allocation.status,0)+1
            if allocation.status!="OK":
                raise SystemExit(f"BLOCKED: allocation {name} {allocation.status}")
            total_seats+=sum(allocation.seats.values())
        seat_sums[i]=total_seats
    if not np.all(seat_sums==350):
        raise SystemExit("BLOCKED: a draw did not allocate exactly 350 seats")
    source_hash=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    result={
        "schema":"ELECTORAL_MONTE_CARLO_10000_V2",
        "status":"PASS",
        "iterations":n,
        "seed":int(args.seed),
        "canonical_seed":SEED,
        "rng":"numpy.PCG64",
        "input":"artifacts/data/election_2023_canonical.json",
        "input_sha256":source_hash,
        "constituencies":52,
        "seats":350,
        "sampler":"Dirichlet-multinomial composition with concentration=200; canonical 2023 territorial matrix; simulation prior, not posterior",
        "concentration":CONCENTRATION,
        "invariants":{"every_draw_seat_sum_350":True,"all_allocations_status_OK":True},
        "allocation_calls":n*52,
        "status_counts":status_counts,
        "predictive_claim":False,
        "fail_closed":True,
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
