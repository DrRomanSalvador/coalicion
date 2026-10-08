#!/usr/bin/env python3
"""Fail-closed audit of the materialized 2023 constituency matrix."""
from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "artifacts/data/election_2023_canonical.json"
HASH = ROOT / "artifacts/data/election_2023_canonical.json.sha256"
REPORT = ROOT / "artifacts/data/election_2023_audit.json"

def fail(msg: str) -> None:
    raise SystemExit("FAIL_CLOSED: " + msg)

def main() -> int:
    if not MATRIX.is_file() or MATRIX.stat().st_size == 0:
        fail("falta matriz 2023 materializada")
    raw = MATRIX.read_bytes()
    actual_sha = hashlib.sha256(raw).hexdigest()
    if HASH.is_file():
        expected_sha = HASH.read_text(encoding="utf-8").strip().split()[0]
        if expected_sha and expected_sha != actual_sha:
            fail("SHA-256 de matriz no coincide")
    data = json.loads(raw.decode("utf-8"))
    if data.get("election") != 2023:
        fail("elección distinta de 2023")
    constituencies = data.get("data", {}).get("constituencies")
    if not isinstance(constituencies, dict) or len(constituencies) != 52:
        fail("no hay exactamente 52 circunscripciones")
    seats = [v.get("seats") for v in constituencies.values()]
    if any(not isinstance(x, int) or x < 1 for x in seats) or sum(seats) != 350:
        fail("escaños inválidos o suma distinta de 350")
    for name, row in constituencies.items():
        parties = row.get("parties")
        blank = row.get("blank_votes")
        valid = row.get("valid_votes")
        if not isinstance(parties, dict) or not parties:
            fail(f"{name}: candidaturas ausentes")
        if not isinstance(blank, int) or blank < 0 or not isinstance(valid, int) or valid < 0:
            fail(f"{name}: votos inválidos")
        if any(not isinstance(p, str) or not p or not isinstance(v, int) or v < 0 for p, v in parties.items()):
            fail(f"{name}: candidatura/votos inválidos")
        if sum(parties.values()) + blank != valid:
            fail(f"{name}: votos válidos != candidaturas + blancos")
    report = {
        "status": "PASS",
        "reason": "STRUCTURAL_VALIDATION",
        "path": str(MATRIX.relative_to(ROOT)),
        "sha256": actual_sha,
        "schema": data.get("schema"),
        "source_tier": data.get("source_tier"),
        "election": 2023,
        "province_count": 52,
        "seat_total": 350,
        "candidate_votes_total": sum(sum(x["parties"].values()) for x in constituencies.values()),
        "valid_vote_keys": len(constituencies),
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
