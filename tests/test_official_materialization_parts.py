from __future__ import annotations

import csv
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARTS = sorted(
    (ROOT / "data/official_materialization_parts").glob(
        "resultados_oficiales_2004_2023.part*.csv"
    )
)
EXPECTED_ROWS = 50_700
EXPECTED_CANONICAL_BYTES = 7_772_611
EXPECTED_CANONICAL_SHA256 = "0b83f9b60e017982c97a702ce24518d5c4432ec90b8e0659210c3db3c9d7634b"
EXPECTED_PARTS = 11
HEADER = [
    "election",
    "fecha_eleccion",
    "circunscripcion",
    "partido",
    "votos",
    "escaños",
    "fuente",
    "nivel_fuente",
]


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_official_parts_reconstruct_exact_canonical_dataset() -> None:
    assert len(PARTS) == EXPECTED_PARTS

    rows = []
    for index, part in enumerate(PARTS):
        with part.open(encoding="utf-8", newline="") as fh:
            parsed = list(csv.reader(fh))
        assert parsed, f"empty materialization part: {part.name}"
        if index == 0:
            assert parsed[0] == HEADER
            parsed = parsed[1:]
        elif parsed[0] == HEADER:
            parsed = parsed[1:]
        rows.extend(parsed)

    assert len(rows) == EXPECTED_ROWS
    assert all(len(row) == len(HEADER) for row in rows)
    assert all(row[7] in {"PRIMARY_INTERIOR", "PRIMARY_OFFICIAL"} for row in rows)


def test_canonical_file_matches_materialized_parts() -> None:
    canonical = ROOT / "data/resultados_oficiales_2004_2023.csv"
    assert canonical.is_file()
    assert canonical.stat().st_size == EXPECTED_CANONICAL_BYTES
    assert _sha256(canonical.read_bytes()) == EXPECTED_CANONICAL_SHA256
    canonical_rows = []
    with canonical.open(encoding="utf-8", newline="") as fh:
        canonical_rows = list(csv.reader(fh))
    part_rows = []
    for index, part in enumerate(PARTS):
        with part.open(encoding="utf-8", newline="") as fh:
            parsed = list(csv.reader(fh))
        if index == 0 and parsed and parsed[0] == HEADER:
            parsed = parsed[1:]
        elif parsed and parsed[0] == HEADER:
            parsed = parsed[1:]
        part_rows.extend(parsed)
    assert canonical_rows[0] == HEADER
    assert canonical_rows[1:] == part_rows
