"""Fail-closed end-to-end election pipeline."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any, Mapping
from src.electoral import allocate
from src.real_estimation_pipeline import PipelineBlocked, validate_territorial_matrix

def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def run_full_election(*, poll: Mapping[str, Any], territorial_votes: Mapping[str, Mapping[str, int]] | None,
                      seats: Mapping[str, int] | None, blank: Mapping[str, int] | None,
                      special: Mapping[str, str] | None = None, output: Path | None = None) -> dict[str, Any]:
    """Survey -> explicit territorial votes -> canonical legal allocation."""
    special = dict(special or {})
    input_hash = _hash({"poll": poll, "territorial_votes": territorial_votes, "seats": seats, "blank": blank, "special": special})
    if territorial_votes is None or seats is None or blank is None:
        result = {"schema":"FULL_ELECTION_PIPELINE_V1","status":"BLOCKED","reason":"BLOCKED_NO_EXPLICIT_TERRITORIAL_INPUT","input_hash":input_hash,"policy":{"national_to_territorial_inference":False,"fail_closed":True}}
    else:
        validate_territorial_matrix(territorial_votes, seats, blank, special)
        constituencies, totals = {}, {}
        for c in sorted(territorial_votes):
            valid = sum(territorial_votes[c].values()) + blank[c]
            allocation = allocate(territorial_votes[c], seats[c], valid, special.get(c, ""), blank[c])
            if allocation.status != "OK":
                raise PipelineBlocked(f"BLOCKED_ELECTORAL_ALLOCATION:{c}:{allocation.status}")
            row = {"votes":dict(sorted(territorial_votes[c].items())),"seats":allocation.seats,"valid_votes":valid}
            constituencies[c] = row
            for party, n in allocation.seats.items():
                totals[party] = totals.get(party, 0) + int(n)
        result = {"schema":"FULL_ELECTION_PIPELINE_V1","status":"PASS","poll":dict(poll),"territory":constituencies,"national_seats":dict(sorted(totals.items())),"input_hash":input_hash,"output_hash":_hash({"territory":constituencies,"national_seats":totals}),"policy":{"national_to_territorial_inference":False,"fail_closed":True}}
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result
