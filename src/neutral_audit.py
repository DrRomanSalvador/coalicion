"""Auditoría estructural fail-closed de una matriz electoral canónica.

No certifica datos ausentes ni sustituye la fuente primaria.
"""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any

EXPECTED_PROVINCES = 52
EXPECTED_SEATS = 350
EXPECTED_SOURCE = "INTERIOR_PRIMARY"

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def audit_canonical(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.is_file():
        return {"status":"BLOCKED","reason":"MISSING_CANONICAL_MATRIX","path":str(p)}
    try:
        data=json.loads(p.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
        return {"status":"BLOCKED","reason":"INVALID_CANONICAL_JSON","detail":str(e),"path":str(p)}
    provinces=data.get("data",{}).get("provinces",[])
    seats=sum(int(x.get("seats",0)) for x in provinces)
    names=[x.get("name") for x in provinces]
    unique=len(names)==len(set(names)) and all(isinstance(x,str) and x for x in names)
    valid=data.get("data",{}).get("valid_votes",{})
    blank=data.get("data",{}).get("blank_votes",{})
    structural = (
        data.get("source")==EXPECTED_SOURCE
        and data.get("election")=="2023"
        and len(provinces)==EXPECTED_PROVINCES
        and seats==EXPECTED_SEATS
        and unique
        and isinstance(valid,dict)
        and set(valid)==set(names)
        and isinstance(blank,dict)
        and set(blank).issubset(set(names))
    )
    return {
        "status":"PASS" if structural else "BLOCKED",
        "reason":"STRUCTURAL_VALIDATION" if structural else "CANONICAL_STRUCTURE_INVALID",
        "path":str(p),
        "sha256":sha256_file(p),
        "source":data.get("source"),
        "election":data.get("election"),
        "province_count":len(provinces),
        "seat_total":seats,
        "valid_vote_keys":len(valid) if isinstance(valid,dict) else None,
    }

if __name__ == "__main__":
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", default="artifacts/data/election_2023_canonical.json")
    print(json.dumps(audit_canonical(ap.parse_args().path),ensure_ascii=False,indent=2))
