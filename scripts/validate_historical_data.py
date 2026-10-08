#!/usr/bin/env python3
"""Fail-closed validator and provenance manifest for Spain historical data."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

RESULTS = Path("data/resultados_oficiales_2004_2023.csv")
POLLS = Path("data/encuestas_historicas_2004_2023.csv")
REGISTRY = Path("config/electoral_sources.json")
MANIFEST = Path("data/manifests/HISTORICAL_DATA_MATERIALIZATION.json")
LIMITATIONS = Path("data/manifests/HISTORICAL_DATA_LIMITATIONS.json")
ACQUISITION = Path("data/manifests/INTERIOR_ACQUISITION.json")
INTERIOR_WORKBOOK = Path("data/raw/Elecciones-Congreso.xlsx")

EXPECTED_DATES = {
    "2004": "2004-03-14", "2008": "2008-03-09", "2011": "2011-11-20",
    "2015": "2015-12-20", "2016": "2016-06-26", "2019A": "2019-04-28",
    "2019N": "2019-11-10", "2023J": "2023-07-23",
}
RESULT_COLUMNS = {
    "election", "fecha_eleccion", "circunscripcion", "partido", "votos", "escaños", "fuente", "nivel_fuente",
}
EXPECTED_ROWS = 50700\nPOLL_COLUMNS = {
    "fecha_encuesta", "partido", "estimacion_voto", "tipo_encuesta",
    "encuesta", "fuente", "nivel_fuente", "metodo", "codigo_estudio",
    "variable", "sample_size",
}


def rows(path: Path):
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit("FAIL-CLOSED: " + message)


def main() -> None:
    require(REGISTRY.is_file(), "canonical source registry missing")
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    require(registry.get("scope") == "Spain", "source registry scope is not Spain")
    require(registry["data_policy"]["primary_source_precedence"] is True, "primary precedence disabled")
    require(registry["data_policy"]["no_synthetic_values"] is True, "synthetic values policy disabled")
    official = registry["official_results"]
    require(any(s["id"] == "interior" and s["role"] == "primary_official" for s in official),
            "Interior primary source missing from registry")
    cis = registry["official_surveys"]
    require(any(s["id"] == "cis" and s["role"] == "primary_official" for s in cis),
            "CIS primary source missing from registry")
    correction = registry["election_scope_correction"]
    require(correction["general_elections_2023"] == "2023-07-23", "2023 election scope is incorrect")
    require(correction["invalid_claim_rejected"] == "2023-11-23", "invalid 2023 date guard missing")

    require(RESULTS.is_file() and RESULTS.stat().st_size > 1000, "official results missing/empty")
    require(POLLS.is_file() and POLLS.stat().st_size > 1000, "CIS surveys missing/empty")
    require(ACQUISITION.is_file() and ACQUISITION.stat().st_size > 100, "Interior acquisition provenance missing")
    acquisition = json.loads(ACQUISITION.read_text(encoding="utf-8"))
    require(acquisition.get("schema") in {"INTERIOR_OFFICIAL_ACQUISITION_V2", "INTERIOR_OFFICIAL_ACQUISITION_V4"}, "invalid Interior acquisition manifest")
    require(acquisition.get("source_url") == "https://descargas.interior.gob.es/datasets/resultados_electorales/Elecciones-Congreso.xlsx",
            "Interior provenance must retain the explicit official XLSX URL")
    require(acquisition.get("sha256") and int(acquisition.get("file_bytes", 0)) > 10000,
            "incomplete Interior provenance")
    require(INTERIOR_WORKBOOK.is_file() and INTERIOR_WORKBOOK.stat().st_size == int(acquisition["file_bytes"]),
            "downloaded Interior workbook is missing or its byte size differs from provenance")
    require(sha256(INTERIOR_WORKBOOK) == acquisition["sha256"],
            "downloaded Interior workbook SHA-256 differs from provenance")

    erows, prows = rows(RESULTS), rows(POLLS)
    require(erows and prows, "historical datasets contain no rows")
    require(set(erows[0]) == RESULT_COLUMNS, f"official schema mismatch: {set(erows[0])}")
    require(set(prows[0]) == POLL_COLUMNS, f"CIS schema mismatch: {set(prows[0])}")

    elections = {r["election"] for r in erows}
    require(elections == set(EXPECTED_DATES), f"election scope mismatch: {elections}")
    require("2023N" not in elections, "invented 2023N election detected")
    require(len(erows) >= 50000, f"official dataset row floor not met: {len(erows)}")
    require(len(erows) == EXPECTED_ROWS, f"official dataset must contain exactly {EXPECTED_ROWS} rows: {len(erows)}")
    require(len(prows) >= 1000, f"CIS minimum not met: {len(prows)} rows")

    require(all(r["nivel_fuente"] in {"PRIMARY_OFFICIAL", "PRIMARY_INTERIOR"} for r in erows), "non-primary official source row")
    require(all(r["nivel_fuente"] == "PRIMARY_OFFICIAL_MICRODATA" for r in prows), "non-primary CIS row")

    result_keys = set()
    for r in erows:
        require(r["fecha_eleccion"] == EXPECTED_DATES[r["election"]], "wrong election date")
        for k in ("election", "fecha_eleccion", "circunscripcion", "partido", "fuente"):
            require(bool(r[k].strip()), f"blank official field: {k}")
        votes = float(r["votos"])
        seats = float(r["escaños"])
        require(votes >= 0 and seats >= 0, "negative official value")
        require(seats.is_integer(), f"non-integer official seats: {r}")
        # The Interior workbook used by the canonical parser does not expose
        # official constituency/party codes in this sheet. Do not synthesize
        # identifiers: uniqueness is checked on the source labels instead.
        key = (r["election"], r["circunscripcion"], r["partido"])
        require(key not in result_keys, f"duplicate official key: {key}")
        result_keys.add(key)

    for r in prows:
        for k in ("fecha_encuesta", "partido", "tipo_encuesta", "fuente", "codigo_estudio", "variable"):
            require(bool(r[k].strip()), f"blank CIS field: {k}")
        v = float(r["estimacion_voto"])
        require(0 <= v <= 100, f"invalid CIS percentage: {v}")
        require(float(r["sample_size"]) > 0, "invalid CIS sample size")

    by_election = {}
    seats_by_election = {}
    for r in erows:
        by_election.setdefault(r["election"], set()).add(r["circunscripcion"])
        seats_by_election[r["election"]] = seats_by_election.get(r["election"], 0) + float(r["escaños"])
    require(set(by_election) == set(EXPECTED_DATES), "constituency coverage missing an election")
    require(all(len(v) == 52 for v in by_election.values()), "each election must have 52 constituencies")
    require(all(v == 350 for v in seats_by_election.values()), "each election must total exactly 350 seats")
    for election in EXPECTED_DATES:
        votes = sum(float(r["votos"]) for r in erows if r["election"] == election)
        require(votes > 0, f"zero national votes for {election}")

    secondary = registry.get("private_pollsters", []) + registry.get("aggregators_discovery", [])
    limitations = []
    for source in secondary:
        limitations.append({
            "id": source.get("id"),
            "name": source.get("name"),
            "status": "NON_CANONICAL_LIMITED",
            "role": source.get("role"),
            "reason": "Secondary/private or discovery source; never overwrites official Interior/CIS canonical observations.",
            "allowed_use": "context, triangulation, sensitivity analysis",
            "not_allowed": "canonical historical materialization or replacement of missing primary values",
        })
    replica = Path("data/secondary/encuestas_historicas_last_poll_replica_2004_2023.csv")
    if replica.is_file():
        limitations.append({
            "id": "secondary_last_poll_replica",
            "name": "Last-poll historical replica",
            "status": "NON_CANONICAL_LIMITED",
            "reason": "Replica retained separately; it is not a CIS primary dataset.",
            "allowed_use": "comparison and diagnostic checks only",
            "not_allowed": "canonical OOS input or overwrite of CIS history",
        })

    manifest = {
        "schema": "HISTORICAL_DATA_MATERIALIZATION_V4",
        "status": "PASS",
        "scope": "Spain; Congress general elections in the official Interior workbook, 2004-2023",
        "scope_note": "The 2023 general election is 2023-07-23 (23J); 2023-11-23 is explicitly rejected.",
        "source_registry": str(REGISTRY),
        "official_results": {
            "path": str(RESULTS), "sha256": sha256(RESULTS), "rows": len(erows),
            "elections": sorted(elections), "source": "Ministerio del Interior",
        },
        "cis_surveys": {
            "path": str(POLLS), "sha256": sha256(POLLS), "rows": len(prows),
            "studies": len({r["codigo_estudio"] for r in prows}),
            "source": "Centro de Investigaciones Sociológicas (CIS)",
            "interpretation": "weighted vote-intention derived from primary CIS microdata; not a reconstructed CIS scenario forecast",
            "limitation": "Do not label these rows as the CIS published scenario forecast unless the corresponding official estimation document is separately ingested.",
        },
        "non_canonical_sources": limitations,
        "certification_gate": {
            "official_results": "PASS",
            "cis_primary_microdata": "PASS",
            "non_canonical_sources": "REPORTED_WITH_LIMITATIONS",
            "synthetic_values": "PROHIBITED",
            "future_leakage": "PROHIBITED",
        },
    }
    manifest["limitations_artifact"] = str(LIMITATIONS)
    LIMITATIONS.parent.mkdir(parents=True, exist_ok=True)
    LIMITATIONS.write_text(json.dumps({
        "schema": "HISTORICAL_DATA_LIMITATIONS_V1",
        "status": "EXPLICIT_NON_CANONICAL_BOUNDARIES",
        "canonical_sources": ["Ministerio del Interior", "Centro de Investigaciones Sociológicas (CIS)"],
        "secondary_sources": limitations,
        "cis_interpretation": manifest["cis_surveys"]["interpretation"],
        "cis_limitation": manifest["cis_surveys"]["limitation"],
        "rules": {
            "synthetic_values": "PROHIBITED",
            "future_leakage": "PROHIBITED",
            "secondary_overwrite": "PROHIBITED",
            "seat_to_vote_backcalculation": "PROHIBITED",
            "national_to_territorial_conversion": "PROHIBITED"
        }
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

# Canonical historical integration validation entrypoint.
