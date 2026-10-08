import json
from pathlib import Path
from scripts.materialize_priority2_checkpoint import main

def test_priority2_national_only_gate_materializes_block():
    assert main() == 0
    result = json.loads(Path("artifacts/phase2_priority2_status.json").read_text(encoding="utf-8"))
    assert result["status"] == "BLOCKED"
    assert result["reason"] == "BLOCKED_NO_EXPLICIT_TERRITORIAL_INPUT"
    assert result["policy"]["national_to_territorial_inference"] is False
