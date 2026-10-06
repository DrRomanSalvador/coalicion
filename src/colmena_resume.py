"""Zero-context resume gate: repository state, not chat history, is authoritative."""
from __future__ import annotations
from pathlib import Path
import json
from .reproducibility_contract import verify_contract
from .error_registry import validate_code, is_blocking

STATE=Path("docs/COLMENA_STATE.json")

def load_state():
    if not STATE.exists():
        raise RuntimeError("STATE_MISSING")
    state=json.loads(STATE.read_text(encoding="utf-8"))
    required=("status","methodology","last_action","last_action_result","next_single_action","blocking_errors")
    missing=[x for x in required if x not in state]
    if missing: raise RuntimeError("STATE_SCHEMA_MISSING:"+",".join(missing))
    if not isinstance(state["next_single_action"],str) or not state["next_single_action"].strip():
        raise RuntimeError("NEXT_SINGLE_ACTION_MISSING")
    for e in state["blocking_errors"]:
        validate_code(e["id"])
        if is_blocking(e["id"]) and e.get("status")=="OPEN":
            continue
    return state

def resume():
    contract=verify_contract()
    state=load_state()
    if contract["status"]!="PASS":
        return {"status":"BLOCKED","reason":"REPRODUCIBILITY_CONTRACT","contract":contract,"next_single_action":state["next_single_action"]}
    return {
        "status":state["status"],
        "last_action":state["last_action"],
        "last_action_result":state["last_action_result"],
        "next_single_action":state["next_single_action"],
        "blocking_errors":[e for e in state["blocking_errors"] if e.get("status")=="OPEN"],
        "contract":contract["contract"]
    }

if __name__=="__main__":
    print(json.dumps(resume(),ensure_ascii=False,indent=2,sort_keys=True))
