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
    provinces=[{"name":f"P{i}","seats":1,"parties":[{"name":"A","votes":10},{"name":"B","votes":5}]} for i in range(52)]
    data={"source":"INTERIOR_PRIMARY","election":"2023","data":{"provinces":provinces,"valid_votes":{f"P{i}":15 for i in range(52)},"blank_votes":{}}}
    p=tmp_path/"matrix.json"
    import json
    p.write_text(json.dumps(data),encoding="utf-8")
    r=audit_canonical(p)
    assert r["status"]=="PASS"
    assert r["province_count"]==52 and r["seat_total"]==52
