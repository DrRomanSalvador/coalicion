from pathlib import Path
from src.neutral_audit import audit_canonical

def test_missing_canonical_is_fail_closed(tmp_path: Path):
    r=audit_canonical(tmp_path/"missing.json")
    assert r["status"]=="BLOCKED"
    assert r["reason"]=="MISSING_CANONICAL_MATRIX"

def test_invalid_canonical_is_fail_closed(tmp_path: Path):
    p=tmp_path/"bad.json"
    p.write_text("{not-json",encoding="utf-8")
    r=audit_canonical(p)
    assert r["status"]=="BLOCKED"
    assert r["reason"]=="INVALID_CANONICAL_JSON"

def test_valid_structure(tmp_path: Path):
    total=24_487_414
    base, rem=divmod(total, 52)
    constituencies={}
    for i in range(52):
        seats=7 if i < 38 else 6
        votes=base + (1 if i < rem else 0)
        constituencies[f"P{i}"]={
            "seats": seats,
            "parties": {"A": votes, "B": 0},
            "blank_votes": 0,
            "valid_votes": votes,
        }
    data={
        "schema":"ELECTION_2023_CONSTITUENCY_MATRIX_V1",
        "election":2023,
        "source_tier":"OFFICIAL_PRIMARY",
        "data":{"constituencies":constituencies},
    }
    p=tmp_path/"matrix.json"
    import json
    p.write_text(json.dumps(data),encoding="utf-8")
    r=audit_canonical(p)
    assert r["status"]=="PASS"
    assert r["province_count"]==52 and r["seat_total"]==350
