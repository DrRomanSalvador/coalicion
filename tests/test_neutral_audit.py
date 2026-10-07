from pathlib import Path
import json
from src.neutral_audit import audit_canonical

ROOT=Path(__file__).resolve().parents[1]

def test_missing_canonical_is_fail_closed(tmp_path: Path):
    r=audit_canonical(tmp_path/"missing.json")
    assert r["status"]=="BLOCKED"
    assert r["reason"]=="MISSING_CANONICAL_MATRIX"

def test_noncanonical_matrix_is_rejected_before_parsing(tmp_path: Path):
    p=tmp_path/"bad.json"
    p.write_text("{not-json",encoding="utf-8")
    r=audit_canonical(p)
    assert r["status"]=="BLOCKED"
    assert r["reason"]=="UNAUTHORIZED_MATRIX_PATH"

def test_canonical_matrix_passes_current_contract():
    r=audit_canonical(ROOT/"artifacts/data/election_2023_canonical.json")
    assert r["status"]=="PASS"
    assert r["province_count"]==52 and r["seat_total"]==350
    assert r["candidate_votes_total"]==24_487_414

def test_canonical_contract_constants_are_pinned():
    from src.neutral_audit import EXPECTED_CANONICAL_PATH, EXPECTED_CANONICAL_SHA256, EXPECTED_CANDIDATE_VOTES
    assert EXPECTED_CANONICAL_PATH=="artifacts/data/election_2023_canonical.json"
    assert EXPECTED_CANONICAL_SHA256=="db2c720fda68ee0be898c874c5aef016dcd6bb02c3593ee6c7ac96bbbf7983bf"
    assert EXPECTED_CANDIDATE_VOTES==24_487_414
