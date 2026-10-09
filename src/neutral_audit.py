"""Auditoría estructural fail-closed de una matriz electoral canónica.

No certifica datos ausentes ni sustituye la fuente primaria.
"""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any

EXPECTED_PROVINCES = 52
EXPECTED_SEATS = 350
EXPECTED_SCHEMA = "ELECTION_2023_CONSTITUENCY_MATRIX_V2"
EXPECTED_SOURCE_TIERS = {"OFFICIAL_PRIMARY"}
EXPECTED_CANDIDATE_VOTES = 24_487_414
EXPECTED_WORKBOOK_SHA256 = "dba3394f1812f338067231bce68acf56af1e13ddf8cfb709a814bcc46357ebc2"
OFFICIAL_WORKBOOK_URL = "https://descargas.interior.gob.es/datasets/resultados_electorales/Elecciones-Congreso.xlsx"
ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "data/manifests/official_interior_congreso.json"
WORKBOOK_PATH = ROOT / "data/raw/Elecciones-Congreso.xlsx"
NORMALIZED_CSV_PATH = ROOT / "data/official_interior_congreso_1977_2023.csv"

def _manifest_value(key: str) -> str:
    try:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        value = manifest.get(key)
        return value if isinstance(value, str) else ""
    except (OSError, json.JSONDecodeError):
        return ""

EXPECTED_CANONICAL_SHA256 = _manifest_value("canonical_2023_sha256")
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
    try:
        relative = p.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        relative = p.as_posix()
    if relative != EXPECTED_CANONICAL_PATH:
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
    try:
        manifest=json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError):
        manifest=None
    source_hash=sha256_file(WORKBOOK_PATH) if WORKBOOK_PATH.is_file() else None
    normalized_hash=sha256_file(NORMALIZED_CSV_PATH) if NORMALIZED_CSV_PATH.is_file() else None
    source_meta=data.get("source",{}) if isinstance(data.get("source"),dict) else {}
    validation=data.get("validation",{}) if isinstance(data.get("validation"),dict) else {}
    seat_recon=validation.get("vote_seat_reconciliation",{}) if isinstance(validation.get("vote_seat_reconciliation"),dict) else {}
    manifest_ok=False
    if isinstance(manifest,dict) and WORKBOOK_PATH.is_file() and NORMALIZED_CSV_PATH.is_file():
        manifest_ok=(
            manifest.get("schema")=="OFFICIAL_INTERIOR_CONGRESS_DATASET_V1"
            and manifest.get("status")=="READY"
            and manifest.get("source_url")==OFFICIAL_WORKBOOK_URL
            and manifest.get("hash_scope")=="workbook_bytes"
            and manifest.get("sha256")==EXPECTED_WORKBOOK_SHA256==source_hash
            and manifest.get("bytes")==WORKBOOK_PATH.stat().st_size
            and manifest.get("canonical_2023_sha256")==digest
            and manifest.get("canonical_2023_bytes")==p.stat().st_size
            and manifest.get("normalized_csv_sha256")==normalized_hash
            and manifest.get("normalized_csv_bytes")==NORMALIZED_CSV_PATH.stat().st_size
            and len(manifest.get("elections",[]))==16
            and manifest.get("constituencies")==52
        )
    structural = (
        data.get("schema")==EXPECTED_SCHEMA
        and data.get("election")==2023
        and data.get("source_tier") in EXPECTED_SOURCE_TIERS
        and source_meta.get("sha256")==source_hash
        and manifest_ok
        and len(provinces)==EXPECTED_PROVINCES
        and seats==EXPECTED_SEATS
        and unique
        and all(isinstance(v,int) and not isinstance(v,bool) and v>=0 for v in valid.values())
        and all(isinstance(v,int) and not isinstance(v,bool) and v>=0 for v in blank.values())
        and all(v == sum(constituencies[k].get("parties",{}).values()) + blank[k] for k,v in valid.items())
        and sum(sum(c.get("parties",{}).values()) for c in provinces)==EXPECTED_CANDIDATE_VOTES
        and digest==EXPECTED_CANONICAL_SHA256
        and recorded_hash==digest
        and validation.get("status")=="PASS"
        and seat_recon.get("status")=="PASS"
        and seat_recon.get("constituencies")==52
        and seat_recon.get("discrepancies")==0
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
        "source_sha256":source_hash,
        "manifest_status":manifest.get("status") if isinstance(manifest,dict) else None,
        "vote_seat_reconciliation":seat_recon,
    }

if __name__ == "__main__":
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", default="artifacts/data/election_2023_canonical.json")
    print(json.dumps(audit_canonical(ap.parse_args().path),ensure_ascii=False,indent=2))
