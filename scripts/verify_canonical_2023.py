#!/usr/bin/env python3
"""Fail-closed structural verifier for the official 2023 Congress canonical matrix."""
from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "artifacts/data/election_2023_canonical.json"
CERT = ROOT / "artifacts/audit/certificate_2023.json"
VALIDATION = ROOT / "artifacts/audit/validation_2023.json"
EXPECTED_PROVINCES = 52
EXPECTED_SEATS = 350

def sha256_json(obj):
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()

def fail(msg):
    raise SystemExit("FAIL_CLOSED: " + msg)

def main():
    for path in (MATRIX, CERT, VALIDATION):
        if not path.is_file() or path.stat().st_size == 0:
            fail(f"falta evidencia obligatoria: {path}")
    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    cert = json.loads(CERT.read_text(encoding="utf-8"))
    validation = json.loads(VALIDATION.read_text(encoding="utf-8"))
    if matrix.get("source") != "INTERIOR_PRIMARY" or matrix.get("election") != "2023":
        fail("fuente/elección canónica inválida")
    if matrix.get("validation", {}).get("audit_status") != "PASS":
        fail("validación matemática no PASS")
    provinces = matrix.get("data", {}).get("provinces")
    if not isinstance(provinces, list) or len(provinces) != EXPECTED_PROVINCES:
        fail("no hay exactamente 52 circunscripciones")
    names = [p.get("name") for p in provinces]
    if any(not isinstance(n, str) or not n.strip() for n in names) or len(set(names)) != EXPECTED_PROVINCES:
        fail("nombres de circunscripción ausentes o duplicados")
    seats = [p.get("seats") for p in provinces]
    if any(not isinstance(s, int) or s < 1 for s in seats) or sum(seats) != EXPECTED_SEATS:
        fail("escaños ausentes o suma distinta de 350")
    valid_votes = matrix.get("data", {}).get("valid_votes", {})
    blank_votes = matrix.get("data", {}).get("blank_votes", {})
    if set(valid_votes) != set(names) or set(blank_votes) != set(names):
        fail("faltan votos válidos o votos en blanco para alguna circunscripción")

    for province in provinces:
        parties = province.get("parties")
        if not isinstance(parties, list) or not parties:
            fail(f"{province.get('name')}: sin candidaturas")
        seen = set()
        for row in parties:
            name, votes = row.get("name"), row.get("votes")
            if not isinstance(name, str) or not name or name in seen:
                fail(f"{province.get('name')}: candidatura inválida/duplicada")
            seen.add(name)
            if not isinstance(votes, int) or votes < 0:
                fail(f"{province.get('name')}/{name}: votos inválidos")
        pname = province["name"]
        party_sum = sum(r["votes"] for r in province["parties"])
        if valid_votes[pname] != party_sum + blank_votes[pname]:
            fail(f"{pname}: votos válidos != candidaturas + blancos")
    expected_merkle = cert.get("merkle_root")
    if matrix.get("validation", {}).get("merkle_root") != expected_merkle:
        fail("Merkle root inconsistente entre matriz y certificado")
    rebuilt = {}
    for province in sorted(provinces, key=lambda x: x["name"]):
        rebuilt[province["name"]] = {r["name"]: r["votes"] for r in sorted(province["parties"], key=lambda x: x["name"])}
    hashes = {
        n: sha256_json({
            "province": n,
            "parties": p,
            "seats": next(x["seats"] for x in provinces if x["name"] == n),
            "valid_votes": valid_votes[n],
            "blank_votes": blank_votes[n],
        })
        for n, p in rebuilt.items()
    }
    level = [bytes.fromhex(hashes[n]) for n in sorted(hashes)]
    while len(level) > 1:
        if len(level) % 2: level.append(level[-1])
        level = [hashlib.sha256(level[i] + level[i+1]).digest() for i in range(0, len(level), 2)]
    if level[0].hex() != expected_merkle:
        fail("Merkle root no reproduce la matriz")
    if validation.get("provinces") != EXPECTED_PROVINCES:
        fail("validation_2023.json no coincide con 52 circunscripciones")
    print("OK: matriz 2023 estructuralmente verificada y fail-closed.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
