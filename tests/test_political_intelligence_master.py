from pathlib import Path
import json

def test_master_manifest_script_and_existing_evidence_contract():
    path = Path("scripts/build_political_intelligence_master_manifest.py")
    assert path.is_file()
    source = path.read_text(encoding="utf-8")
    assert "COALICION_POLITICAL_INTELLIGENCE_MASTER_V1" in source
    assert "self_certification_forbidden" in source

def test_existing_poll_coverage_is_explicitly_primary_limited():
    data=json.loads(Path("ci_evidence/poll_source_coverage.json").read_text(encoding="utf-8"))
    assert data["status"]=="PASS"
    assert data["fail_closed"] is True
    assert "evidence_limit" in data
