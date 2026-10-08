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
EXPECTED_BYTES = 7_721_910
EXPECTED_SHA256 = "fe438253477b0b5d6976161baf1ea17879e8ad8e25691e0320752fdd642409fe"
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

    raw = b"".join(p.read_bytes() for p in PARTS)
    assert len(raw) == EXPECTED_BYTES
    assert _sha256(raw) == EXPECTED_SHA256

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
    raw = b"".join(p.read_bytes() for p in PARTS)
    assert canonical.read_bytes() == raw
