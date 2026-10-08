import json
from pathlib import Path
from src.trailability.evidence import build_record, validate_records

ROOT=Path("data/surveys/october_2026/territorial")

def test_three_current_territorial_observations_have_traceability():
    files=sorted(p for p in ROOT.glob("*.json") if p.name != "index.json")
    assert len(files) >= 3
    required={"survey_id","source_id","fieldwork_start","fieldwork_end","publication_date","sample_size","methodology","source_url","content_sha256"}
    for path in files:
        data=json.loads(path.read_text(encoding="utf-8"))
        assert required <= data.keys(), path
        assert data["source_url"].startswith("https://")
        assert len(data["content_sha256"]) == 64, path
        assert data["scope"] == "territorial"

def test_territorial_records_cannot_be_used_as_general_constituency_data():
    for path in ROOT.glob("*.json"):
        if path.name == "index.json":
            continue
        data=json.loads(path.read_text(encoding="utf-8"))
        assert data["policy"]["not_general_election_constituency_data"] is True


def test_territorial_records_pass_evidence_contract():
    records=[]
    for path in ROOT.glob("*.json"):
        if path.name == "index.json":
            continue
        data=json.loads(path.read_text(encoding="utf-8"))
        records.append(build_record(data, content_sha256=data["content_sha256"]))
    result=validate_records(records, require_primary=True)
    assert result["status"]=="PASS"
    assert result["records"]==3
