#!/usr/bin/env python3
"""Materialize deterministic reproducibility evidence for Phase 2."""
from pathlib import Path
import json, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.reproducibility.hasher import reproducibility_record
from src.reproducibility.verifier import verify_same_result
from src.pipeline.full_election import run_full_election

OUT=ROOT/"artifacts/phase2_reproducibility_status.json"

def main()->int:
    votes={f"c{i}":{"A":6000+i,"B":4000-i} for i in range(1,53)}
    seats={f"c{i}":6 for i in range(1,53)}
    seats["c1"]=44
    blank={f"c{i}":100 for i in range(1,53)}
    poll={"id":"reproducible-demo","PP":33.2,"PSOE":28.5,"Vox":12.8,"Sumar":13.0}
    a=run_full_election(poll=poll,territorial_votes=votes,seats=seats,blank=blank)
    b=run_full_election(poll=poll,territorial_votes=votes,seats=seats,blank=blank)
    verification=verify_same_result(input_value={"poll":poll,"votes":votes,"seats":seats,"blank":blank},output_a=a,output_b=b)
    record=reproducibility_record(
        input_value={"poll":poll,"votes":votes,"seats":seats,"blank":blank},
        output_value=a,
        code_files=[ROOT/"src/pipeline/full_election.py",ROOT/"src/electoral.py",ROOT/"src/reproducibility/hasher.py",ROOT/"src/reproducibility/verifier.py"],
    )
    result={"schema":"PHASE2_REPRODUCIBILITY_STATUS_V1","status":"PASS" if a["status"]=="PASS" and verification["status"]=="PASS" else "BLOCKED","verification":verification,"record":record,"fail_closed":True}
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    assert result["status"]=="PASS"
    return 0
if __name__=="__main__": raise SystemExit(main())
