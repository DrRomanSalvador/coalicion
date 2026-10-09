"""Regression tests for the official-only 2023 matrix entrypoint.

The old territorial-slug fallback was removed when matrix acquisition became
official-source-only. These tests guard the replacement contract rather than
reintroducing a secondary-source compatibility API.
"""
from pathlib import Path

from scripts import acquire_2023_matrix as acquisition


def test_2023_entrypoint_uses_pinned_interior_workbook():
    assert acquisition.OFFICIAL_SOURCE_ID == "MINISTERIO_DEL_INTERIOR"
    assert acquisition.WORKBOOK.as_posix().endswith("data/raw/Elecciones-Congreso.xlsx")
    assert acquisition.MANIFEST.as_posix().endswith("data/manifests/official_interior_congreso.json")


def test_2023_entrypoint_delegates_to_single_official_materializer():
    source = Path(acquisition.__file__).read_text(encoding="utf-8")
    assert "scripts/materialize_official_interior_dataset.py" in source
    assert "secondary_fallback" in source
    assert "False" in source
    assert "BLOCKED: official canonical matrix or vote-seat reconciliation invalid" in source
