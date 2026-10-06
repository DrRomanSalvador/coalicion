import json
from pathlib import Path

def test_supplied_2023_national_overview_is_arithmetically_consistent():
    p=Path("artifacts/data/election_2023_national.json")
    d=json.loads(p.read_text(encoding="utf-8"))
    assert d["election"] == 2023
    assert d["candidate_ballots"] + d["blank_votes"] == d["valid_votes"]
    assert d["valid_votes"] + d["null_votes"] == d["voters"]
    assert d["voters"] + d["abstentions"] == d["census"]
    assert sum(x["votes"] for x in d["candidacies"]) == d["candidate_ballots"]
    assert sum(x["seats"] for x in d["candidacies"]) == 350

def test_national_overview_does_not_claim_constituency_matrix():
    d=json.loads(Path("artifacts/data/election_2023_national.json").read_text(encoding="utf-8"))
    assert d["scope"] == "Ambito Nacional"
    assert d["source_tier"] == "SECONDARY_REPLICA_VERIFIED"
