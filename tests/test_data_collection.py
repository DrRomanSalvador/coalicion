import json
from pathlib import Path

import pytest

from src.data import normalize_registry


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/surveys/current_2026/current_national.json"


def test_current_registry_normalizes_with_provenance_hashes():
    result = normalize_registry(SOURCE)
    assert result["count"] >= 10
    assert result["source_registry_hash"]
    assert result["normalized_hash"]
    assert all(row["source_url"] for row in result["surveys"])


def test_official_mode_rejects_secondary_reconciled_rows():
    with pytest.raises(ValueError, match="PRIMARY_VERIFIED"):
        normalize_registry(SOURCE, official=True)
