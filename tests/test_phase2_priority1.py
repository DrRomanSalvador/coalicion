import json
from pathlib import Path

from scripts.verify_phase2_priority1 import main

def test_priority1_gate_is_fail_closed_and_materializes_status():
    rc = main()
    path = Path("artifacts/phase2_priority1_status.json")
    assert path.is_file()
    status = json.loads(path.read_text(encoding="utf-8"))
    assert status["status"] in {"PASS", "BLOCKED"}
    assert status["policy"]["fail_closed"] is True
    assert status["national_survey_count"] >= 0
    assert rc == (0 if status["status"] == "PASS" else 2)

def test_current_registry_has_at_least_ten_records():
    data = json.loads(Path("data/surveys/current_2026/current_national.json").read_text(encoding="utf-8"))
    assert len(data["surveys"]) >= 10
