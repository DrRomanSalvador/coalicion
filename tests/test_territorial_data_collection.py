import json
from pathlib import Path

ROOT=Path("data/surveys/october_2026/territorial")

def test_three_current_territorial_observations_have_traceability():
    files=sorted(ROOT.glob("*.json"))
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
        data=json.loads(path.read_text(encoding="utf-8"))
        assert data["policy"]["not_general_election_constituency_data"] is True
