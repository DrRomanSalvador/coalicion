#!/usr/bin/env python3
"""REINA-SEEC v3: aggressive evidence acquisition, still fail-closed.

v3 adds verified acquisition paths (official Infoelectoral/Interior and
published eleccionesdb snapshots) but never promotes corroboration into the
canonical matrix. It delegates canonical parsing/validation to the repository's
existing deterministic pipeline.
"""
from __future__ import annotations

import hashlib
import json
import os
import ssl
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"
RAW = ART / "queen_bee_v3_sources"
LOG = ART / "queen_bee_v3_report.json"
RAW.mkdir(parents=True, exist_ok=True)

SOURCES = [
    {"id": "INTERIOR_XLSX", "tier": "PRIMARY",
     "url": "https://descargas.interior.gob.es/datasets/resultados_electorales/Elecciones-Congreso.xlsx",
     "role": "official_vote_matrix", "kind": "xlsx"},
    {"id": "INTERIOR_RESULTS", "tier": "PRIMARY",
     "url": "https://infoelectoral.interior.gob.es/es/elecciones-celebradas/resultados-electorales/",
     "role": "official_results_portal", "kind": "html"},
    {"id": "INTERIOR_DOWNLOADS", "tier": "PRIMARY",
     "url": "https://infoelectoral.interior.gob.es/es/elecciones-celebradas/area-de-descargas/",
     "role": "official_download_catalog", "kind": "html"},
    {"id": "BOE_2023", "tier": "PRIMARY",
     "url": "https://www.boe.es/buscar/doc.php?id=BOE-A-2023-18907",
     "role": "official_results_and_seats", "kind": "html"},
    {"id": "ELECCIONESDB_CSV", "tier": "SECONDARY",
     "url": "https://data.spainelectoralproject.com/eleccionesdb-etl/descargas/eleccionesdb_csv.zip",
     "role": "corroboration_snapshot", "kind": "zip"},
    {"id": "ELECCIONESDB_SQLITE", "tier": "SECONDARY",
     "url": "https://data.spainelectoralproject.com/eleccionesdb-etl/descargas/eleccionesdb_sqlite.zip",
     "role": "corroboration_snapshot", "kind": "zip"},
    {"id": "ELECCIONESDB_PARQUET", "tier": "SECONDARY",
     "url": "https://data.spainelectoralproject.com/eleccionesdb-etl/descargas/eleccionesdb_parquet.zip",
     "role": "corroboration_snapshot", "kind": "zip"},
]

def now() -> str:
    return datetime.now(timezone.utc).isoformat()

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def fetch(source: dict, attempts: int = 4) -> dict:
    name = source["id"] + "_" + hashlib.sha256(source["url"].encode()).hexdigest()[:12]
    out = RAW / name
    last = None
    for attempt in range(1, attempts + 1):
        try:
            req = Request(source["url"], headers={
                "User-Agent": "REINA-SEEC/3.0",
                "Accept": "*/*",
                "Connection": "close",
            })
            ctx = ssl.create_default_context()
            with urlopen(req, timeout=90, context=ctx) as response:
                data = response.read()
                status = getattr(response, "status", 200)
                content_type = response.headers.get("Content-Type", "")
            if status != 200 or not data:
                raise RuntimeError(f"invalid_http_response status={status} bytes={len(data)}")
            # A ZIP/XLSX response must have a recognizable magic signature.
            if source["kind"] in {"zip", "xlsx"} and not (data[:2] == b"PK"):
                raise RuntimeError("unexpected_binary_signature")
            out.write_bytes(data)
            return {
                "status": "SUCCESS", "attempt": attempt, "path": str(out.relative_to(ROOT)),
                "bytes": len(data), "sha256": sha256(out), "content_type": content_type,
            }
        except (HTTPError, URLError, TimeoutError, OSError, RuntimeError) as exc:
            last = {"status": "FAILED", "attempt": attempt,
                    "error": f"{type(exc).__name__}: {exc}"}
            if attempt < attempts:
                time.sleep(min(2 ** attempt, 20))
    return last or {"status": "FAILED", "error": "unknown"}

def run_cmd(task: str, argv: list[str], retries: int = 3, timeout: int = 900) -> dict:
    for attempt in range(1, retries + 1):
        try:
            p = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
            if p.returncode == 0:
                return {"task": task, "status": "PASS", "attempt": attempt,
                        "stdout": p.stdout[-12000:], "stderr": p.stderr[-12000:]}
            result = {"task": task, "status": "FAIL_CLOSED" if attempt == retries else "RETRY",
                      "attempt": attempt, "stdout": p.stdout[-12000:], "stderr": p.stderr[-12000:]}
        except subprocess.TimeoutExpired as exc:
            result = {"task": task, "status": "TIMEOUT", "attempt": attempt,
                      "stdout": str(exc.stdout or ""), "stderr": str(exc.stderr or "")}
        if attempt < retries:
            time.sleep(10 * attempt)
    return result

def main() -> int:
    report = {"timestamp": now(), "version": "v3", "sources": [], "tasks": []}

    for source in SOURCES:
        result = fetch(source)
        report["sources"].append({**source, **result})
        print(f"[{result['status']}] {source['id']}")

    # Existing exhaustive acquisition records all configured sources and hashes;
    # this is evidence collection, not permission to fabricate a canonical matrix.
    report["tasks"].append(run_cmd(
        "exhaustive_sources",
        [sys.executable, "scripts/exhaustive_data_acquisition.py", "--search", "--resolve"],
    ))

    # Canonical engine remains authoritative for parsing and schema validation.
    report["tasks"].append(run_cmd(
        "canonical_acquisition",
        [sys.executable, "scripts/ai_electoral_data_engine.py", "--retry-on-fail"],
    ))

    canonical = ROOT / "artifacts/data/election_2023_canonical.json"
    if canonical.is_file():
        report["tasks"].append(run_cmd(
            "verify_canonical",
            [sys.executable, "scripts/verify_canonical_2023.py"],
        ))
    else:
        report["tasks"].append({
            "task": "verify_canonical", "status": "BLOCKED_NO_PRIMARY_CANONICAL",
        })

    primary_success = any(
        x.get("tier") == "PRIMARY" and
        x.get("role") in {"official_vote_matrix", "official_results_and_seats"} and
        x.get("status") == "SUCCESS"
        for x in report["sources"]
    )
    verification_ok = any(
        x.get("task") == "verify_canonical" and x.get("status") == "PASS"
        for x in report["tasks"]
    )
    report["status"] = "COMPLETE" if primary_success and verification_ok else "PARTIAL_FAIL_CLOSED"
    report["fail_closed"] = True
    report["canonical_present"] = canonical.is_file()
    LOG.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "canonical_present": report["canonical_present"],
                      "primary_source_observed": primary_success, "verification_ok": verification_ok},
                     ensure_ascii=False, indent=2))
    return 0 if report["status"] == "COMPLETE" else 1

if __name__ == "__main__":
    raise SystemExit(main())
