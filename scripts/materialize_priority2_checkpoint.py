#!/usr/bin/env python3
"""Materialize the Priority 2 national-only pipeline gate."""
from pathlib import Path
from src.pipeline.full_election import run_full_election

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/phase2_priority2_status.json"

def main() -> int:
    result = run_full_election(
        poll={"id":"national-only-demo","PP":33.2,"PSOE":28.5,"Vox":12.8,"Sumar":13.0},
        territorial_votes=None,
        seats=None,
        blank=None,
        output=OUT,
    )
    assert result["status"] == "BLOCKED"
    assert result["reason"] == "BLOCKED_NO_EXPLICIT_TERRITORIAL_INPUT"
    assert result["policy"]["national_to_territorial_inference"] is False
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
