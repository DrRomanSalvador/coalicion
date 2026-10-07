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
EXPECTED_CANDIDATE_VOTES = 24_487_414
EXPECTED_CANONICAL_SHA256 = "db07f35c862a1a7c620b3242d2b1ddda041b2b68765427385ae41d958b6d3cb2"
EXPECTED_CANONICAL_PATH = "artifacts/data/election_2023_canonical.json"

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
    if p.as_posix() != EXPECTED_CANONICAL_PATH:
        return {"status":"BLOCKED","reason":"UNAUTHORIZED_MATRIX_PATH","path":str(p)}
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
    digest=sha256_file(p)
    recorded_hash=None
    sidecar=p.with_name(p.name + ".sha256")
    if sidecar.is_file():
        recorded_hash=sidecar.read_text(encoding="utf-8").strip().split()[0]
    structural = (
        data.get("schema")==EXPECTED_SCHEMA
        and data.get("election")==2023
        and data.get("source_tier") in EXPECTED_SOURCE_TIERS
        and len(provinces)==EXPECTED_PROVINCES
        and seats==EXPECTED_SEATS
        and unique
        and all(isinstance(v,int) and v>=0 for v in valid.values())
        and all(isinstance(v,int) and v>=0 for v in blank.values())
        and all(v == sum(constituencies[k].get("parties",{}).values()) + blank[k] for k,v in valid.items())
        and sum(sum(c.get("parties",{}).values()) for c in provinces)==EXPECTED_CANDIDATE_VOTES
        and digest==EXPECTED_CANONICAL_SHA256
        and recorded_hash==EXPECTED_CANONICAL_SHA256
    )
    return {
        "status":"PASS" if structural else "BLOCKED",
        "reason":"STRUCTURAL_VALIDATION" if structural else "CANONICAL_STRUCTURE_INVALID",
        "path":str(p),
        "sha256":digest,
        "recorded_sha256":recorded_hash,
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
