#!/usr/bin/env python3
"""
AI Electoral Data Engine 2023 — REINA-SEEC.

Motor reproducible de:
1) adquisición,
2) normalización,
3) validación matemática,
4) reconciliación con precedencia de fuente,
5) auditoría criptográfica,
6) generación de matriz canónica.

IMPORTANTE:
- La IA no "corrige" cifras oficiales mediante promedios.
- Una fuente PRIMARY prevalece sobre cualquier réplica SECONDARY.
- Las discrepancias se registran; no se ocultan.
- INE padrón y CIS son fuentes auxiliares/metodológicas y no se mezclan
  como si fueran votos electorales.
- Si faltan datos críticos, el resultado queda PARTIAL/BLOCKED.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "official"
PROCESSED = ROOT / "data" / "processed"
AUDIT = ROOT / "artifacts" / "audit"
DATA = ROOT / "artifacts" / "data"
LOG = ROOT / "artifacts" / "execution_log.md"

INTERIOR_URL = "https://descargas.interior.gob.es/datasets/resultados_electorales/Elecciones-Congreso.xlsx"
INTERIOR_PATH = RAW / "Elecciones-Congreso.xlsx"

# Only sources whose role is semantically comparable are reconciled as votes.
# Secondary sources are optional corroboration, never arithmetic averaging.
SOURCES = {
    "interior": {
        "authority": "Ministerio del Interior",
        "type": "PRIMARY",
        "url": INTERIOR_URL,
        "path": INTERIOR_PATH,
    },
    "ine_pobmun": {
        "authority": "Instituto Nacional de Estadística",
        "type": "PRIMARY_AUXILIARY",
        "url": "https://www.ine.es/pob_xls/pobmun.zip",
        "path": RAW / "ine" / "pobmun.zip",
    },
    "cis_catalog": {
        "authority": "Centro de Investigaciones Sociológicas",
        "type": "PRIMARY_AUXILIARY",
        "url": "https://www.cis.es/es/estudios/catalogo?catalogo=estudio",
        "path": ROOT / "data" / "live" / "CIS_CATALOGO_ESTUDIOS.html",
    },
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_json(obj) -> str:
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True,
                     separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def log(message: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"- {now()} — {message}\n")


def fetch(url: str, destination: Path, timeout: int = 120) -> dict:
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp = destination.with_suffix(destination.suffix + ".part")
    req = Request(url, headers={"User-Agent": "REINA-SEEC/1.0"})
    try:
        with urlopen(req, timeout=timeout) as response, tmp.open("wb") as out:
            shutil.copyfileobj(response, out, 1024 * 1024)
        if tmp.stat().st_size == 0:
            raise RuntimeError("respuesta vacía")
        tmp.replace(destination)
    except (HTTPError, URLError, TimeoutError, OSError, RuntimeError):
        tmp.unlink(missing_ok=True)
        raise
    return {
        "source_url": url,
        "retrieved_at": now(),
        "path": str(destination.relative_to(ROOT)),
        "size_bytes": destination.stat().st_size,
        "sha256": sha256_file(destination),
    }


def acquire(force: bool = False) -> dict:
    acquired = {}
    failures = []
    for name, cfg in SOURCES.items():
        path = cfg["path"]
        try:
            if path.exists() and not force:
                meta = {
                    "source_url": cfg["url"],
                    "retrieved_at": now(),
                    "path": str(path.relative_to(ROOT)),
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                    "status": "existing_snapshot",
                }
            else:
                meta = fetch(cfg["url"], path)
                meta["status"] = "downloaded"
            acquired[name] = {**cfg, **meta}
            log(f"ACQUIRE {name}: OK sha256={meta['sha256']}")
        except Exception as exc:
            failures.append(name)
            log(f"ACQUIRE {name}: ERROR {type(exc).__name__}: {exc}")
    return {"sources": acquired, "failures": failures}


def normalise_text(value) -> str:
    return " ".join(str(value or "").strip().split())


def is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def parse_interior(path: Path) -> dict:
    """Parsea tablas provinciales del XLSX sin alterar etiquetas electorales."""
    try:
        import openpyxl
    except ImportError as exc:
        raise RuntimeError("openpyxl es obligatorio para parsear Interior") from exc

    def norm(v):
        return "".join(c for c in str(v or "").lower() if c.isalnum())

    def find(headers, *names):
        ns = {norm(x) for x in names}
        for i, h in enumerate(headers):
            if norm(h) in ns:
                return i
        for i, h in enumerate(headers):
            nh = norm(h)
            if any(n in nh or nh in n for n in ns if n):
                return i
        return None

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    rows = []
    for ws in wb.worksheets:
        it = ws.iter_rows(values_only=True)
        headers = list(next(it, ()))
        if not headers:
            continue
        p = find(headers, "Provincia", "Circunscripción", "Province")
        party = find(headers, "Candidatura", "Candidaturas", "Partido", "Siglas")
        votes = find(headers, "Votos", "Votos candidatura")
        if p is None or party is None or votes is None:
            continue
        for row in it:
            if len(row) <= max(p, party, votes):
                continue
            province = normalise_text(row[p])
            candidacy = normalise_text(row[party])
            value = row[votes]
            if not province or not candidacy or not is_number(value) or value < 0:
                continue
            rows.append({
                "sheet": ws.title,
                "province": province,
                "party": candidacy,
                "votes": int(value),
            })

    if not rows:
        raise RuntimeError(
            "No se encontró tabla provincia/candidatura/votos en Interior."
        )

    matrix = defaultdict(lambda: defaultdict(int))
    for row in rows:
        matrix[row["province"]][row["party"]] += row["votes"]

    return {
        "source": "interior",
        "provinces": {p: dict(sorted(v.items())) for p, v in sorted(matrix.items())},
        "row_count": len(rows),
    }


def validate_vote_matrix(data: dict) -> dict:
    anomalies = []
    provinces = data.get("provinces", {})
    total_votes = 0

    for province, parties in provinces.items():
        if not parties:
            anomalies.append({
                "type": "EMPTY_PROVINCE",
                "severity": "CRITICAL",
                "province": province,
            })
            continue
        for party, votes in parties.items():
            if not isinstance(votes, int) or votes < 0:
                anomalies.append({
                    "type": "INVALID_VOTE",
                    "severity": "CRITICAL",
                    "province": province,
                    "party": party,
                    "value": votes,
                })
            total_votes += votes if isinstance(votes, int) and votes >= 0 else 0

    # Benford NO se usa como prueba de fraude: con datos electorales agregados
    # y muchos ceros/candidaturas pequeñas su potencia diagnóstica es limitada.
    # Solo se conserva como señal descriptiva.
    first_digits = []
    for parties in provinces.values():
        for votes in parties.values():
            if votes >= 10:
                first_digits.append(int(str(votes)[0]))
    benford_note = {
        "applicable": len(first_digits) >= 100,
        "sample_size": len(first_digits),
        "interpretation": "descriptive_only; never a fraud verdict",
    }

    status = "PASS" if not any(a["severity"] == "CRITICAL" for a in anomalies) else "FAIL"
    return {
        "status": status,
        "provinces": len(provinces),
        "total_party_votes": total_votes,
        "anomalies": anomalies,
        "benford": benford_note,
    }


def reconcile_primary_only(normalized: dict[str, dict]) -> dict:
    """
    Construye la matriz electoral desde la fuente primaria.
    Si aparecen otras matrices electorales compatibles en el futuro,
    se comparan celda a celda y se registra el conflicto; no se promedia.
    """
    primary = normalized.get("interior")
    if not primary:
        raise RuntimeError("BLOCKED: no existe fuente primaria Interior")

    conflicts = []
    for name, other in normalized.items():
        if name == "interior" or "provinces" not in other:
            continue
        common_provinces = set(primary["provinces"]) & set(other["provinces"])
        for province in common_provinces:
            common_parties = (
                set(primary["provinces"][province])
                & set(other["provinces"][province])
            )
            for party in common_parties:
                a = primary["provinces"][province][party]
                b = other["provinces"][province][party]
                if a != b:
                    conflicts.append({
                        "province": province,
                        "party": party,
                        "primary_value": a,
                        "secondary_value": b,
                        "resolution": "PRIMARY_WINS",
                        "secondary_source": name,
                    })

    return {
        "provinces": primary["provinces"],
        "source": "INTERIOR_PRIMARY",
        "conflicts": conflicts,
    }


def merkle_root(items: list[str]) -> str:
    if not items:
        return hashlib.sha256(b"EMPTY").hexdigest()
    level = [bytes.fromhex(x) for x in items]
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        level = [
            hashlib.sha256(level[i] + level[i + 1]).digest()
            for i in range(0, len(level), 2)
        ]
    return level[0].hex()


def audit(matrix: dict, acquired: dict, validation: dict, conflicts: list) -> dict:
    province_hashes = {}
    for province, parties in matrix["provinces"].items():
        province_hashes[province] = sha256_json({
            "province": province,
            "parties": parties,
        })

    source_hashes = {
        name: meta["sha256"]
        for name, meta in acquired.items()
        if meta.get("sha256")
    }

    root = merkle_root([province_hashes[p] for p in sorted(province_hashes)])
    reconciliation_hash = sha256_json(matrix)

    certificate = {
        "schema_version": "1.0",
        "generated_at": now(),
        "election": "2023",
        "source_of_truth": "INTERIOR_PRIMARY",
        "validation_status": validation["status"],
        "province_count": len(matrix["provinces"]),
        "province_hashes": province_hashes,
        "merkle_root": root,
        "source_hashes": source_hashes,
        "reconciliation_hash": reconciliation_hash,
        "conflicts_count": len(conflicts),
        "conflicts_resolution": "PRIMARY_WINS",
        "limitations": [
            "No se certifican 52 circunscripciones hasta verificar estructura completa del XLSX.",
            "No se infiere número de escaños desde votos si el workbook no lo aporta.",
            "Fuentes auxiliares no se mezclan aritméticamente con votos oficiales.",
        ],
    }
    return certificate


def canonical(matrix: dict, certificate: dict) -> dict:
    provinces = []
    for name in sorted(matrix["provinces"]):
        provinces.append({
            "name": name,
            "seats": None,
            "parties": [
                {"name": party, "votes": votes}
                for party, votes in sorted(matrix["provinces"][name].items())
            ],
        })

    status = (
        "READY_FOR_VOTE_ENGINE"
        if certificate["province_count"] == 52
        and certificate["validation_status"] == "PASS"
        else "PARTIAL"
    )

    return {
        "schema_version": "1.0",
        "election": "2023",
        "type": "general",
        "source": "INTERIOR_PRIMARY",
        "validation": {
            "status": status,
            "audit_status": certificate["validation_status"],
            "reconciliation_hash": certificate["reconciliation_hash"],
            "merkle_root": certificate["merkle_root"],
        },
        "data": {"provinces": provinces},
    }


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def run(force: bool = False) -> int:
    print("=== AI ELECTORAL DATA ENGINE 2023 ===")

    acquired_result = acquire(force=force)
    acquired = acquired_result["sources"]

    if "interior" not in acquired:
        print("BLOCKED: fuente primaria Interior no disponible.")
        return 1

    normalized = {}
    try:
        normalized["interior"] = parse_interior(INTERIOR_PATH)
        log("PARSE interior: OK")
    except Exception as exc:
        log(f"PARSE interior: ERROR {type(exc).__name__}: {exc}")
        print(f"BLOCKED: parse Interior: {exc}")
        return 1

    validation = validate_vote_matrix(normalized["interior"])
    write_json(AUDIT / "validation_2023.json", validation)

    if validation["status"] != "PASS":
        print("BLOCKED: validación matemática crítica fallida.")
        return 1

    matrix = reconcile_primary_only(normalized)
    conflicts = matrix["conflicts"]

    certificate = audit(
        matrix,
        acquired,
        validation,
        conflicts,
    )

    canon = canonical(matrix, certificate)

    write_json(AUDIT / "certificate_2023.json", certificate)
    write_json(DATA / "election_2023_canonical.json", canon)
    write_json(AUDIT / "reconciliation_2023.json", {
        "source_of_truth": "INTERIOR_PRIMARY",
        "conflicts": conflicts,
        "resolution": "PRIMARY_WINS",
    })

    log(
        f"AUDIT 2023: validation={validation['status']} "
        f"provinces={len(matrix['provinces'])} "
        f"conflicts={len(conflicts)} "
        f"merkle={certificate['merkle_root']}"
    )

    print(f"Provincias: {len(matrix['provinces'])}")
    print(f"Votos de candidaturas: {validation['total_party_votes']}")
    print(f"Conflictos: {len(conflicts)}")
    print(f"Merkle root: {certificate['merkle_root']}")
    print(f"Matriz: {DATA / 'election_2023_canonical.json'}")
    print(f"Certificado: {AUDIT / 'certificate_2023.json'}")

    if canon["validation"]["status"] != "READY_FOR_VOTE_ENGINE":
        print("ESTADO: PARTIAL — faltan elementos para certificación integral.")
        return 2

    print("ESTADO: READY_FOR_VOTE_ENGINE")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    return run(force=args.force)


if __name__ == "__main__":
    raise SystemExit(main())
