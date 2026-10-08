import json
from pathlib import Path
from scripts.materialize_reproducibility_checkpoint import main

def test_reproducibility_evidence_materializes():
    assert main() == 0
    data=json.loads(Path("artifacts/phase2_reproducibility_status.json").read_text(encoding="utf-8"))
    assert data["status"]=="PASS"
    assert data["verification"]["status"]=="PASS"
    assert data["record"]["fail_closed"] is True
