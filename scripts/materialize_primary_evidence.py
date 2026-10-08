#!/usr/bin/env python3
"""Materialize primary public evidence into a CI artifact, fail-closed."""
from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
import ssl

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "primary_evidence"
INTERIOR = "https://descargas.interior.gob.es/datasets/resultados_electorales/Elecciones-Congreso.xlsx"
BOE = "https://www.boe.es/buscar/doc.php?id=BOE-A-2023-15066"
BOE_CORRECTION = "https://www.boe.es/buscar/doc.php?id=BOE-A-2023-15828"
BOE_RESULTS = "https://www.boe.es/buscar/doc.php?id=BOE-A-2023-18907"

def fetch(url: str, path: Path) -> dict:
    ctx = ssl.create_default_context()
    req = Request(url, headers={"User-Agent": "COALICION/primary-evidence"})
    with urlopen(req, context=ctx, timeout=90) as r:
        data = r.read()
        content_type = r.headers.get("Content-Type", "")
    if not data:
        raise RuntimeError(f"BLOCKED: empty primary response: {url}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return {
        "url": url,
        "path": str(path.relative_to(ROOT)),
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "content_type": content_type,
    }

def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    records = [
        fetch(INTERIOR, OUT / "Elecciones-Congreso.xlsx"),
        fetch(BOE, OUT / "BOE-A-2023-15066.html"),
        fetch(BOE_CORRECTION, OUT / "BOE-A-2023-15828.html"),
        fetch(BOE_RESULTS, OUT / "BOE-A-2023-18907.html"),
    ]
    manifest = {
        "schema": "COALICION_PRIMARY_EVIDENCE_MANIFEST_V1",
        "status": "MATERIALIZED",
        "records": records,
        "policy": {"primary_only": True, "synthetic_values": False, "fail_closed": True},
    }
    (OUT / "MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": manifest["status"], "records": len(records)}, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
