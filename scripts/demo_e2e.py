#!/usr/bin/env python3
"""Demostración E2E reproducible con la matriz electoral 2023 versionada.

Usa una circunscripción real (Madrid, elección de 2023), no encuestas ni
proyecciones. La réplica está etiquetada como secundaria y no certificada.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = ROOT / "artifacts/data/election_2023_canonical.json"
AUDIT_PATH = ROOT / "artifacts/data/election_2023_audit.json"
PARTIES = ("PARTIDO SOCIALISTA OBRERO ESPAÑOL - PSOE", "SUMAR - SUMAR")


def main() -> int:
    matrix_bytes = MATRIX_PATH.read_bytes()
    matrix = json.loads(matrix_bytes)
    audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))

    if audit.get("status") != "PASS":
        raise SystemExit(f"BLOCKED: audit de matriz no pasa: {audit.get('status')}")
    if audit.get("source_tier") != "SECONDARY_REPLICA_VERIFIED":
        raise SystemExit("BLOCKED: la procedencia no está etiquetada como réplica secundaria")
    if audit.get("province_count") != 52 or audit.get("seat_total") != 350:
        raise SystemExit("BLOCKED: la matriz no satisface las invariantes 52/350")

    row = matrix["data"]["constituencies"].get("Madrid")
    if not row:
        raise SystemExit("BLOCKED: falta Madrid en la matriz 2023")
    votes = row["parties"]
    missing = [party for party in PARTIES if party not in votes]
    if missing:
        raise SystemExit(f"BLOCKED: candidaturas ausentes en Madrid: {missing}")
    if sum(votes.values()) + row["blank_votes"] != row["valid_votes"]:
        raise SystemExit("BLOCKED: votos de Madrid no reconcilian con votos válidos")

    payload = {
        "votes": {"Madrid": votes},
        "seats": {"Madrid": row["seats"]},
        "valid_votes": {"Madrid": row["valid_votes"]},
        "blank": {"Madrid": row["blank_votes"]},
        "special": {},
    }
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", suffix=".json", delete=False
    ) as handle:
        json.dump(payload, handle, ensure_ascii=False)
        input_path = Path(handle.name)

    try:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "coalicion.py"), "coalition", *PARTIES,
             "--input", str(input_path)],
            cwd=ROOT, text=True, capture_output=True, check=False,
        )
    finally:
        input_path.unlink(missing_ok=True)

    if proc.returncode != 0:
        raise SystemExit("BLOCKED: CLI de coalición falló\n" + proc.stderr + proc.stdout)

    result = json.loads(proc.stdout)
    separate = result["total_separate"]
    combined = result["total_coalition"]
    if not isinstance(separate, int) or not isinstance(combined, int):
        raise SystemExit("BLOCKED: la CLI no devolvió totales enteros")
    if sum(result["separate_seats_by_constituency"].values()) != separate:
        raise SystemExit("BLOCKED: el total separado no reconcilia")
    if sum(result["coalition_seats_by_constituency"].values()) != combined:
        raise SystemExit("BLOCKED: el total coaligado no reconcilia")
    if result["delta"] != combined - separate:
        raise SystemExit("BLOCKED: delta de escaños inconsistente")

    print(json.dumps({
        "demo_status": "PASS",
        "election": 2023,
        "constituency": "Madrid",
        "constituency_seats": row["seats"],
        "data_status": "SECONDARY_REPLICA_VERIFIED",
        "official_certification": "NOT_CLAIMED",
        "source_provider": matrix.get("source", {}).get("provider"),
        "matrix_sha256_runtime": hashlib.sha256(matrix_bytes).hexdigest(),
        "coalition": list(PARTIES),
        "seats_separate": separate,
        "seats_coalition": combined,
        "delta_seats": result["delta"],
        "input_hash": result["certificate_input_hash"],
        "canonical_engine": result["canonical_engine"],
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
