#!/usr/bin/env python3
"""Reproducible 10k electoral Monte Carlo over the canonical 2023 matrix."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from src.electoral import allocate

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",default="artifacts/data/election_2023_canonical.json")
    ap.add_argument("--output",default="ci_evidence/mc_10000.json")
    ap.add_argument("--iterations",type=int,default=10000)
    ap.add_argument("--seed",type=int,default=20261008)
    args=ap.parse_args()
    if args.iterations<10000: raise SystemExit("BLOCKED: iterations must be >= 10000")
    x=json.loads(Path(args.input).read_text(encoding="utf-8")); cs=x["data"]["constituencies"]
    if len(cs)!=52 or sum(v["seats"] for v in cs.values())!=350: raise SystemExit("BLOCKED: canonical matrix must contain 52 constituencies and 350 seats")
    rng=np.random.Generator(np.random.PCG64(args.seed)); draws=[]
    for _ in range(args.iterations):
        national={}
        for name,row in cs.items():
            parties=row["parties"]; total=sum(int(v) for v in parties.values())
            if total<=0: raise SystemExit(f"BLOCKED: {name}: empty votes")
            alpha=np.maximum(np.asarray(list(parties.values()),dtype=float),1.0)*200.0/total
            sampled=rng.multinomial(total,rng.dirichlet(alpha))
            votes={p:int(v) for p,v in zip(parties,sampled)}
            valid=sum(votes.values())+int(row.get("blank_votes",0))
            result=allocate(votes,int(row["seats"]),valid,blank_votes=int(row.get("blank_votes",0)))
            if result.status!="OK": raise SystemExit(f"BLOCKED: {name}: {result.status}")
            for p,s in result.seats.items(): national[p]=national.get(p,0)+s
        if sum(national.values())!=350: raise SystemExit("BLOCKED: seat conservation")
        draws.append(national)
    parties=sorted({p for d in draws for p in d})
    def q(p,qv): return float(np.quantile([d.get(p,0) for d in draws],qv,method="linear"))
    out={"schema":"ELECTORAL_MONTE_CARLO_10000_V1","status":"PASS","iterations":args.iterations,"seed":args.seed,"rng":"numpy.PCG64","input":args.input,"constituencies":52,"seats":350,"sampler":"Dirichlet-multinomial constituency perturbation; concentration=200; explicit simulation prior, not posterior","p10":{p:q(p,.10) for p in parties},"p50":{p:q(p,.50) for p in parties},"p90":{p:q(p,.90) for p in parties},"probability_at_least_one_seat":{p:sum(d.get(p,0)>=1 for d in draws)/args.iterations for p in parties},"invariants":{"every_draw_seat_sum_350":True,"all_allocations_status_OK":True},"fail_closed":True}
    p=Path(args.output); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); print(json.dumps(out,ensure_ascii=False,indent=2))
if __name__=="__main__": main()
