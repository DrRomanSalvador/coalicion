import json
from pathlib import Path

def test_national_input_remains_consistent():
    d=json.loads(Path("artifacts/data/election_2023_national.json").read_text(encoding="utf-8"))
    assert d["candidate_ballots"] == sum(x["votes"] for x in d["candidacies"])
    assert sum(x["seats"] for x in d["candidacies"]) == 350

def test_matrix_acquisition_contract_is_fail_closed_and_primary_only():
    p=Path("scripts/acquire_2023_matrix.py")
    s=p.read_text(encoding="utf-8")
    assert "MINISTERIO_DEL_INTERIOR" in s
    assert "materialize_official_interior_dataset.py" in s
    assert "secondary_fallback" in s
    assert "BLOCKED" in s
    assert "DATO_ELECTORAL" not in s
