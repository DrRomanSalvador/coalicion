"""Auditoría estructural fail-closed de una matriz electoral canónica.

No certifica datos ausentes ni sustituye la fuente primaria.
"""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any
from .electoral import allocate

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
    if not isinstance(data,dict):
        return {"status":"BLOCKED","reason":"INVALID_CANONICAL_ROOT","path":str(p)}
    if not isinstance(data.get("data"),dict) or not isinstance(data["data"].get("constituencies"),dict):
        return {"status":"BLOCKED","reason":"INVALID_CONSTITUENCY_MAP","path":str(p)}
    constituencies=data["data"]["constituencies"]
    if any(not isinstance(item,dict) for item in constituencies.values()):
        return {"status":"BLOCKED","reason":"INVALID_CONSTITUENCY_RECORD","path":str(p)}
    provinces=list(constituencies.values())
    names=list(constituencies.keys())
    seat_values=[x.get("seats") for x in provinces]
    seats_valid=all(isinstance(v,int) and not isinstance(v,bool) and v>=1 for v in seat_values)
    seats=sum(v for v in seat_values if isinstance(v,int) and not isinstance(v,bool))
    unique=len(names)==len(set(names)) and len(names)==52 and all(isinstance(x,str) and x for x in names)
    valid={k:v.get("valid_votes") for k,v in constituencies.items()}
    blank={k:v.get("blank_votes") for k,v in constituencies.items()}
    parties_valid=all(isinstance(item.get("parties"),dict) and bool(item.get("parties")) and all(isinstance(p,str) and p and isinstance(v,int) and not isinstance(v,bool) and v>=0 for p,v in item["parties"].items()) for item in provinces)
    candidate_total=sum(sum(item["parties"].values()) for item in provinces) if parties_valid else -1
    blank_total=sum(v for v in blank.values() if isinstance(v,int) and not isinstance(v,bool) and v>=0)
    valid_total=sum(v for v in valid.values() if isinstance(v,int) and not isinstance(v,bool) and v>=0)
    digest=sha256_file(p)
    recorded_hash=None
    sidecar=p.with_name(p.name + ".sha256")
    if sidecar.is_file():
        try:
            sidecar_tokens=sidecar.read_text(encoding="utf-8").strip().split()
            recorded_hash=sidecar_tokens[0] if sidecar_tokens else None
        except OSError:
            recorded_hash=None
    try:
        manifest=json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError):
        manifest=None
    source_hash=sha256_file(WORKBOOK_PATH) if WORKBOOK_PATH.is_file() else None
    normalized_hash=sha256_file(NORMALIZED_CSV_PATH) if NORMALIZED_CSV_PATH.is_file() else None
    source_meta=data.get("source",{}) if isinstance(data.get("source"),dict) else {}
    validation=data.get("validation",{}) if isinstance(data.get("validation"),dict) else {}
    manifest_recon=validation.get("vote_seat_reconciliation",{}) if isinstance(validation.get("vote_seat_reconciliation"),dict) else {}
    recon_differences=[]
    for name,item in constituencies.items():
        try:
            special=name if name in {"Ceuta","Melilla"} else ""
            allocation=allocate(item.get("parties",{}),item.get("seats",0),item.get("valid_votes",0),special,item.get("blank_votes",0))
            expected={party:n for party,n in allocation.seats.items() if n>0} if allocation.status=="OK" else {}
            observed=item.get("observed_seats",{})
            if allocation.status!="OK" or expected!=observed:
                recon_differences.append({"constituency":name,"status":allocation.status,"observed":observed,"calculated":expected})
        except (AttributeError,TypeError,ValueError) as exc:
            recon_differences.append({"constituency":name,"status":"INVALID_INPUT","detail":str(exc)})
    seat_recon={"status":"PASS" if len(constituencies)==52 and not recon_differences else "BLOCKED","constituencies":len(constituencies),"discrepancies":len(recon_differences),"method":"src.electoral.allocate","special_rules":["Ceuta","Melilla"],"details":recon_differences}
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
            and isinstance(manifest.get("elections"),list)
            and manifest.get("elections")==[
                "1977-06-15","1979-03-01","1982-10-28","1986-06-22",
                "1989-10-29","1993-06-06","1996-03-03","2000-03-12",
                "2004-03-14","2008-03-09","2011-11-20","2015-12-20",
                "2016-06-26","2019-04-28","2019-11-10","2023-07-23",
            ]
            and manifest.get("records")==322556
            and manifest.get("constituencies")==52
        )
    structural = (
        data.get("schema")==EXPECTED_SCHEMA
        and data.get("election")==2023
        and data.get("source_tier") in EXPECTED_SOURCE_TIERS
        and source_meta.get("sha256")==source_hash
        and manifest_ok
        and len(provinces)==EXPECTED_PROVINCES
        and seats_valid
        and seats==EXPECTED_SEATS
        and unique
        and all(isinstance(v,int) and not isinstance(v,bool) and v>=0 for v in valid.values())
        and all(isinstance(v,int) and not isinstance(v,bool) and v>=0 for v in blank.values())
        and parties_valid
        and all(v == sum(constituencies[k]["parties"].values()) + blank[k] for k,v in valid.items())
        and candidate_total==EXPECTED_CANDIDATE_VOTES
        and blank_total==200_673
        and valid_total==24_688_087
        and digest==EXPECTED_CANONICAL_SHA256
        and recorded_hash==digest
        and validation.get("status")=="PASS"
        and manifest_recon.get("status")=="PASS"
        and manifest_recon.get("constituencies")==52
        and manifest_recon.get("discrepancies")==0
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
        "candidate_votes_total":candidate_total,
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
