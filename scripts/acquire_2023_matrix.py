#!/usr/bin/env python3
"""Compatibility entrypoint for the single official 2023 matrix materializer.

This script deliberately has no secondary-source fallback. The canonical matrix
must come from the pinned Ministry of the Interior workbook and pass the shared
electoral engine's exact vote-seat reconciliation.
"""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OFFICIAL_SOURCE_ID = "MINISTERIO_DEL_INTERIOR"
WORKBOOK = ROOT / "data/raw/Elecciones-Congreso.xlsx"
MANIFEST = ROOT / "data/manifests/official_interior_congreso.json"
CANONICAL = ROOT / "artifacts/data/election_2023_canonical.json"
ACQUISITION = ROOT / "artifacts/data/election_2023_matrix_acquisition.json"


def main() -> int:
    if not WORKBOOK.is_file():
        from src.data import download_workbook
        download_workbook(WORKBOOK)
    command = [
        sys.executable,
        str(ROOT / "scripts/materialize_official_interior_dataset.py"),
        "--input", "data/raw/Elecciones-Congreso.xlsx",
        "--output-csv", "data/official_interior_congreso_1977_2023.csv",
        "--canonical-2023", "artifacts/data/election_2023_canonical.json",
        "--manifest", "data/manifests/official_interior_congreso.json",
    ]
    subprocess.run(command, cwd=ROOT, check=True)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    validation = manifest.get("validated_2023", {})
    reconciliation = validation.get("vote_seat_reconciliation", {})
    if (
        manifest.get("status") != "READY"
        or manifest.get("sha256") != "dba3394f1812f338067231bce68acf56af1e13ddf8cfb709a814bcc46357ebc2"
        or validation.get("status") != "PASS"
        or reconciliation.get("status") != "PASS"
        or reconciliation.get("discrepancies") != 0
    ):
        raise SystemExit("BLOCKED: official canonical matrix or vote-seat reconciliation invalid")
    ACQUISITION.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "OFFICIAL_2023_MATRIX_ACQUISITION_V2",
        "status": "PASS",
        "source": OFFICIAL_SOURCE_ID,
        "source_sha256": manifest["sha256"],
        "canonical_sha256": manifest["canonical_2023_sha256"],
        "normalized_csv_sha256": manifest["normalized_csv_sha256"],
        "elections": len(manifest["elections"]),
        "constituencies": manifest["constituencies"],
        "validation": validation,
        "secondary_fallback": False,
        "fail_closed": True,
    }
    ACQUISITION.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
