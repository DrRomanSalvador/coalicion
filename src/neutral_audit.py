"""Auditoría estructural fail-closed de una matriz electoral canónica.

No certifica datos ausentes ni sustituye la fuente primaria.
"""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any

EXPECTED_PROVINCES = 52
EXPECTED_SEATS = 350
EXPECTED_SCHEMA = "ELECTION_2023_CONSTITUENCY_MATRIX_V1"
EXPECTED_SOURCE_TIERS = {"OFFICIAL_PRIMARY", "SECONDARY_REPLICA_VERIFIED"}

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
    constituencies=data.get("data",{}).get("constituencies",{})
    provinces=list(constituencies.values())
    names=list(constituencies.keys())
    seats=sum(int(x.get("seats",0)) for x in provinces)
    unique=len(names)==len(set(names)) and len(names)==52 and all(isinstance(x,str) and x for x in names)
    valid={k:v.get("valid_votes") for k,v in constituencies.items()}
    blank={k:v.get("blank_votes",0) for k,v in constituencies.items()}
    structural = (
        data.get("schema")==EXPECTED_SCHEMA
        and data.get("election")==2023
        and data.get("source_tier") in EXPECTED_SOURCE_TIERS
        and len(provinces)==EXPECTED_PROVINCES
        and seats==EXPECTED_SEATS
        and unique
        and all(isinstance(v,int) and v>=0 for v in valid.values())
        and all(isinstance(v,int) and v>=0 for v in blank.values())
        and all(v == sum(c.get("parties",{}).values()) + blank[k] for k,v in valid.items())
        and sum(sum(c.get("parties",{}).values()) for c in provinces)==24487414
    )
    return {
        "status":"PASS" if structural else "BLOCKED",
        "reason":"STRUCTURAL_VALIDATION" if structural else "CANONICAL_STRUCTURE_INVALID",
        "path":str(p),
        "sha256":sha256_file(p),
        "schema":data.get("schema"),
        "source_tier":data.get("source_tier"),
        "election":data.get("election"),
        "province_count":len(provinces),
        "seat_total":seats,
        "candidate_votes_total":sum(sum(c.get("parties",{}).values()) for c in provinces),
        "valid_vote_keys":len(valid),
    }

if __name__ == "__main__":
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", default="artifacts/data/election_2023_canonical.json")
    print(json.dumps(audit_canonical(ap.parse_args().path),ensure_ascii=False,indent=2))
