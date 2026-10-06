#!/usr/bin/env python3
"""Acquire 2023 evidence through Interior, BOE/JEC and EleccionesDB.

Policy:
- Interior XLSX remains the canonical PRIMARY source when obtainable.
- BOE/JEC is an official PRIMARY_ALTERNATIVE evidence source, not an automatic
  replacement for the canonical Interior matrix.
- EleccionesDB is SECONDARY corroboration.
- Raw files are hashed and signature-checked.
- A secondary hash mismatch is never treated as a data conflict: formats differ.
- No source is promoted to canonical by this script.
"""
from __future__ import annotations

import hashlib
import json
import ssl
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "data"
OUT.mkdir(parents=True, exist_ok=True)

INTERIOR_URL = "https://descargas.interior.gob.es/datasets/resultados_electorales/Elecciones-Congreso.xlsx"
BOE_URL = "https://www.boe.es/buscar/doc.php?id=BOE-A-2023-18907"
ELECCIONESDB_URLS = [
    "https://data.spainelectoralproject.com/eleccionesdb-etl/descargas/eleccionesdb_csv.zip",
    "https://data.spainelectoralproject.com/eleccionesdb-etl/descargas/eleccionesdb_sqlite.zip",
    "https://data.spainelectoralproject.com/eleccionesdb-etl/descargas/eleccionesdb_parquet.zip",
]

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def fetch(url: str, path: Path, attempts: int = 4) -> dict:
    last = None
    for attempt in range(1, attempts + 1):
        try:
            req = Request(url, headers={
                "User-Agent": "REINA-SEEC/4.0",
                "Accept": "*/*",
                "Connection": "close",
            })
            ctx = ssl.create_default_context()
            with urlopen(req, timeout=90, context=ctx) as response:
                data = response.read()
                status = getattr(response, "status", 200)
                content_type = response.headers.get("Content-Type", "")
            if status != 200 or not data:
                raise RuntimeError(f"invalid_response status={status} bytes={len(data)}")
            path.write_bytes(data)
            return {
                "status": "SUCCESS",
                "attempt": attempt,
                "bytes": len(data),
                "sha256": sha256_bytes(data),
                "content_type": content_type,
                "path": str(path.relative_to(ROOT)),
            }
        except (HTTPError, URLError, TimeoutError, OSError, RuntimeError) as exc:
            last = {"status": "FAILED", "attempt": attempt,
                    "error": f"{type(exc).__name__}: {exc}"}
            if attempt < attempts:
                time.sleep(min(2 ** attempt, 20))
    return last or {"status": "FAILED", "error": "unknown"}

def validate_binary_signature(path: Path, kind: str) -> tuple[bool, str]:
    head = path.read_bytes()[:8]
    if kind in {"xlsx", "zip"}:
        ok = head[:2] == b"PK"
        return ok, "zip_container" if ok else "unexpected_binary_signature"
    return True, "text"

def parse_boe(path: Path) -> dict:
    try:
        import pandas as pd
        tables = pd.read_html(path, flavor="lxml")
    except Exception as exc:
        return {"status": "PARSE_FAILED", "error": f"{type(exc).__name__}: {exc}"}

    useful = []
    for index, table in enumerate(tables):
        if table.empty:
            continue
        text = " ".join(str(x) for x in table.astype(str).fillna("").to_numpy().ravel())
        if "Total escaños" in text or "Albacete" in text or "Asturias" in text:
            useful.append({"index": index, "rows": len(table), "columns": len(table.columns)})
    return {
        "status": "PARSED",
        "tables": len(tables),
        "useful_tables": useful,
        "note": "BOE Cuadro II contains provincial votes/seats for elected parties; it is not by itself a complete candidature×constituency matrix.",
    }

def run() -> int:
    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "election": "2023",
        "policy": {
            "interior_is_canonical_primary": True,
            "boe_is_primary_alternative_evidence": True,
            "eleccionesdb_is_secondary_only": True,
            "invented_values": False,
            "automatic_secondary_promotion": False,
        },
        "sources": {},
    }

    interior = fetch(INTERIOR_URL, OUT / "raw_interior_2023.xlsx", attempts=5)
    result["sources"]["Interior_XLSX"] = interior
    if interior["status"] == "SUCCESS":
        ok, reason = validate_binary_signature(OUT / "raw_interior_2023.xlsx", "xlsx")
        result["sources"]["Interior_XLSX"]["signature_ok"] = ok
        result["sources"]["Interior_XLSX"]["signature_reason"] = reason
        if not ok:
            result["sources"]["Interior_XLSX"]["status"] = "FAILED_INVALID_SIGNATURE"

    boe = fetch(BOE_URL, OUT / "raw_boe_2023.html", attempts=4)
    result["sources"]["BOE_2023"] = boe
    if boe["status"] == "SUCCESS":
        result["sources"]["BOE_2023"]["parse"] = parse_boe(OUT / "raw_boe_2023.html")

    db_results = []
    for index, url in enumerate(ELECCIONESDB_URLS, 1):
        path = OUT / f"raw_eleccionesdb_2023_{index}.zip"
        item = fetch(url, path, attempts=3)
        item["url"] = url
        if item["status"] == "SUCCESS":
            ok, reason = validate_binary_signature(path, "zip")
            item["signature_ok"] = ok
            item["signature_reason"] = reason
            if not ok:
                item["status"] = "FAILED_INVALID_SIGNATURE"
        db_results.append(item)
    result["sources"]["EleccionesDB"] = db_results

    interior_ok = (
        interior.get("status") == "SUCCESS"
        and result["sources"]["Interior_XLSX"].get("signature_ok") is True
    )
    boe_ok = (
        boe.get("status") == "SUCCESS"
        and result["sources"]["BOE_2023"].get("parse", {}).get("status") == "PARSED"
    )
    db_ok = any(x.get("status") == "SUCCESS" and x.get("signature_ok") is True for x in db_results)

    if interior_ok:
        result["status"] = "PRIMARY_INTERIOR_AVAILABLE"
    elif boe_ok:
        result["status"] = "PRIMARY_ALTERNATIVE_EVIDENCE_AVAILABLE"
    else:
        result["status"] = "PRIMARY_EVIDENCE_UNAVAILABLE"

    result["corroboration"] = {
        "boe_available": boe_ok,
        "eleccionesdb_available": db_ok,
        "status": "PENDING_CELL_LEVEL_RECONCILIATION",
        "reason": "Different source formats/hashes cannot be compared by raw hash. Cell-level reconciliation is required before any canonical promotion.",
    }

    out = OUT / "acquisition_result.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "interior": interior.get("status"),
        "boe": boe.get("status"),
        "eleccionesdb_successes": sum(x.get("status") == "SUCCESS" for x in db_results),
        "result": str(out.relative_to(ROOT)),
    }, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(run())
