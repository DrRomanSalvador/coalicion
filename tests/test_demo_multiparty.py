from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.demo_multiparty import (
    DEFAULT_DATA,
    DEFAULT_SCENARIOS,
    EXPECTED_GIT_BLOB_SHA,
    DemoError,
    build_lists,
    git_blob_sha,
    load_dataset,
    run_demo,
)


def test_canonical_dataset_blob_is_pinned():
    assert git_blob_sha(DEFAULT_DATA.read_bytes()) == EXPECTED_GIT_BLOB_SHA
    load_dataset(DEFAULT_DATA)


def test_fragmented_scenario_reproduces_observed_seats():
    result = run_demo()
    fragmented = result["scenarios"][0]
    assert fragmented["id"] == "fragmentado"
    for region in ("Madrid", "Barcelona"):
        assert fragmented["regions"][region]["simulated_seats"] == result["constituencies"][region]["observed_seats"]
        assert fragmented["regions"][region]["seat_total"] == result["constituencies"][region]["seats"]


def test_grouping_preserves_all_votes():
    parties = {"PSOE": 1000, "SUMAR": 500, "PP": 1200, "ZERO": 0}
    result = build_lists(parties, {"Bloque": ["PSOE", "SUMAR"]})
    assert result == {"Bloque": 1500, "PP": 1200, "ZERO": 0}
    assert sum(result.values()) == sum(parties.values())


def test_duplicate_assignment_fails_closed():
    with pytest.raises(DemoError, match="más de una vez"):
        build_lists({"A": 100, "B": 200, "C": 300}, {"Uno": ["A", "B"], "Dos": ["A", "C"]})


def test_unknown_party_fails_closed():
    with pytest.raises(DemoError, match="no encontrada"):
        build_lists({"A": 100, "B": 200}, {"Bloque": ["A", "NO EXISTE"]})


def test_single_party_group_is_rejected():
    with pytest.raises(DemoError, match="Grupo inválido"):
        build_lists({"A": 100}, {"Bloque": ["A"]})


def test_config_hash_and_scenario_count_are_reported():
    result = run_demo()
    assert len(result["scenarios"]) == 3
    assert len(result["provenance"]["scenario_config_sha256"]) == 64
    assert result["provenance"]["canonical_dataset_git_blob_sha1"] == EXPECTED_GIT_BLOB_SHA


def test_modified_dataset_fails_closed(tmp_path: Path):
    data = json.loads(DEFAULT_DATA.read_text(encoding="utf-8"))
    data["election"] = 2019
    path = tmp_path / "changed.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(DemoError, match="Esquema o elección|blob canónico"):
        load_dataset(path)


def test_modified_scenario_config_fails_on_contract(tmp_path: Path):
    config = json.loads(DEFAULT_SCENARIOS.read_text(encoding="utf-8"))
    config["scenarios"].pop()
    path = tmp_path / "scenarios.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(DemoError, match="tres escenarios"):
        run_demo(DEFAULT_DATA, path)
