import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_weekly_audit_exists_and_is_fail_closed():
    p=ROOT/"scripts/weekly_survey_audit.py"
    assert p.is_file()
    s=p.read_text(encoding="utf-8")
    assert "coverage_limit" in s
    assert "WEEKLY_VIGILANCE_AUDIT_BLOCKED" in s
