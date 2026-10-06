"""Zero-context resume gate: repository state, not chat history, is authoritative."""
from __future__ import annotations
from pathlib import Path
from hashlib import sha256
import json
from .reproducibility_contract import verify_contract
from .error_registry import validate_code, is_blocking

STATE = Path("docs/COLMENA_STATE.json")
INVOCATION = Path("docs/INVOCACION_COLMENA.md")
CONTRACT = Path("CONTRATO_MAESTRO_IA.md")
CANONICAL_METHOD = "SEEC"
CANONICAL_VERSION = "4.0"
CANONICAL_RNG = "numpy.PCG64"
CANONICAL_SEED = 20261006

def load_state(root: Path = Path(".")):
    path = root / STATE
    if not path.exists():
        raise RuntimeError("COLMENA_STATE_MISSING")
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError("COLMENA_STATE_INVALID") from exc
    if state.get("schema") != "COLMENA_STATE_V1":
        raise RuntimeError("COLMENA_STATE_INVALID")
    if state.get("methodology") != CANONICAL_METHOD or state.get("methodology_version") != CANONICAL_VERSION:
        raise RuntimeError("METHOD_MISMATCH")
    if state.get("canonical_rng") != CANONICAL_RNG or state.get("canonical_seed") != CANONICAL_SEED:
        raise RuntimeError("SEED_MISMATCH")
    action = state.get("next_single_action")
    if not isinstance(action, str) or not action.strip():
        raise RuntimeError("MULTIPLE_NEXT_ACTIONS")
    if not (root / INVOCATION).exists():
        raise RuntimeError("INVOCATION_MISSING")
    if not (root / CONTRACT).exists():
        raise RuntimeError("CONTRACT_MISSING")
    for item in state.get("blocking_errors", []):
        validate_code(item["id"])
    return state

def resume(root: Path = Path(".")):
    state = load_state(root)
    contract = verify_contract(root)
    blockers = [e for e in state.get("blocking_errors", []) if e.get("status") == "OPEN" and is_blocking(e["id"])]
    state_bytes = (root / STATE).read_bytes()
    return {
        "status": state.get("status", "UNKNOWN"),
        "fail_closed": bool(state.get("fail_closed")),
        "state_sha256": sha256(state_bytes).hexdigest(),
        "last_verified_commit": state.get("last_verified_commit"),
        "last_action": state.get("last_action"),
        "last_action_result": state.get("last_action_result"),
        "open_blockers": [e["id"] for e in blockers],
        "next_single_action": state["next_single_action"],
        "contract_status": contract["status"]
    }

if __name__ == "__main__":
    print(json.dumps(resume(), ensure_ascii=False, sort_keys=True))
