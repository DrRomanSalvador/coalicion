#!/usr/bin/env python3
"""Strict validation and provenance manifest for Spain historical electoral data.\n\nEvery published historical dataset must pass this validator first.\n"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

RESULTS = Path("data/resultados_oficiales_2004_2023.csv")
POLLS = Path("data/encuestas_historicas_2004_2023.csv")
MANIFEST = Path("data/manifests/HISTORICAL_DATA_MATERIALIZATION.json")

EXPECTED_ELECTIONS = {"2004", "2008", "2011", "2015", "2016", "2019A", "2019N", "2023J"}
RESULT_COLUMNS = {
    "election", "fecha_eleccion", "circunscripcion_codigo", "circunscripcion",
    "partido_codigo", "partido", "votos", "escaños", "fuente", "nivel_fuente",
}
POLL_COLUMNS = {
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
    require(RESULTS.is_file() and RESULTS.stat().st_size > 1000, "official results missing/empty")
    require(POLLS.is_file() and POLLS.stat().st_size > 1000, "CIS surveys missing/empty")

    erows = rows(RESULTS)
    prows = rows(POLLS)
    require(erows, "official results contain no rows")
    require(prows, "CIS surveys contain no rows")

    require(set(erows[0]) == RESULT_COLUMNS, f"official schema mismatch: {set(erows[0])}")
    require(set(prows[0]) == POLL_COLUMNS, f"CIS schema mismatch: {set(prows[0])}")

    elections = {r["election"] for r in erows}
    require(elections == EXPECTED_ELECTIONS, f"election scope mismatch: {elections}")
    require("2023N" not in elections, "invented 2023N election detected")

    require(len(erows) >= 50000, f"unexpectedly small official dataset: {len(erows)} rows")
    require(len(prows) >= 1000, f"CIS minimum not met: {len(prows)} rows")

    require(all(r["nivel_fuente"] == "PRIMARY_OFFICIAL" for r in erows), "non-primary official source row")
    require(all(r["nivel_fuente"] == "PRIMARY_OFFICIAL_MICRODATA" for r in prows), "non-primary CIS row")

    for r in erows:
        for k in ("election", "fecha_eleccion", "circunscripcion", "partido", "fuente"):
            require(bool(r[k].strip()), f"blank official field: {k}")
        require(float(r["votos"]) >= 0 and float(r["escaños"]) >= 0, "negative official value")

    for r in prows:
        for k in ("fecha_encuesta", "partido", "tipo_encuesta", "fuente", "codigo_estudio", "variable"):
            require(bool(r[k].strip()), f"blank CIS field: {k}")
        v = float(r["estimacion_voto"])
        require(0 <= v <= 100, f"invalid CIS percentage: {v}")
        require(float(r["sample_size"]) > 0, "invalid CIS sample size")

    by_election = {}
    for r in erows:
        by_election.setdefault(r["election"], set()).add(r["circunscripcion"])
    require(all(len(v) == 52 for v in by_election.values()), "each election must have 52 constituencies")

    manifest = {
        "schema": "HISTORICAL_DATA_MATERIALIZATION_V2",
        "status": "PASS",
        "scope": "Spain; Congress general elections represented in the official Interior workbook, 2004-2023",
        "scope_note": "The 2023 general election is 2023-07-23 (23J). No 2023-11 general election is included.",
        "official_results": {
            "path": str(RESULTS),
            "sha256": sha256(RESULTS),
            "rows": len(erows),
            "elections": sorted(elections),
            "source": "Ministerio del Interior",
        },
        "cis_surveys": {
            "path": str(POLLS),
            "sha256": sha256(POLLS),
            "rows": len(prows),
            "studies": len({r["codigo_estudio"] for r in prows}),
            "source": "Centro de Investigaciones Sociológicas (CIS)",
            "interpretation": "weighted declared vote-intention from primary microdata; not a reconstructed CIS seat forecast",
        },
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
