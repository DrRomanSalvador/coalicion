from __future__ import annotations

import json
import subprocess
import sys
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
    assert result["official_certification"] == "NOT_INDEPENDENTLY_CERTIFIED"
    assert all(v > 0 for scenario in result["scenarios"] for region in scenario["regions"].values() for v in region["votes_by_list"].values())


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



def test_each_scenario_conserves_votes_and_seats():
    result = run_demo()
    _, constituencies, _ = load_dataset(DEFAULT_DATA)
    assert len(result["scenarios"]) == 3
    for scenario in result["scenarios"]:
        for region, outcome in scenario["regions"].items():
            assert sum(outcome["votes_by_list"].values()) == sum(constituencies[region]["parties"].values())
            assert outcome["seat_total"] == constituencies[region]["seats"]


def test_cli_persists_valid_json_atomically(tmp_path: Path):
    output = tmp_path / "nested" / "demo.json"
    proc = subprocess.run(
        [sys.executable, str(Path(__file__).parents[1] / "scripts/demo_multiparty.py"),
         "--output", str(output)],
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    written = json.loads(output.read_text(encoding="utf-8"))
    printed = json.loads(proc.stdout)
    assert written == printed
    assert written["official_certification"] == "NOT_INDEPENDENTLY_CERTIFIED"



def test_counterfactual_scenario_results_are_pinned():
    # Exact results are regression-locked against the canonical 2023 matrix.
    result = run_demo()
    scenarios = {item["id"]: item for item in result["scenarios"]}
    left = scenarios["izquierda_sin_psoe"]["regions"]
    broad = scenarios["bloque_amplio_con_psoe_psc"]["regions"]
    assert left["Madrid"]["simulated_seats"]["Bloque izquierda sin PSOE"] == 6
    assert left["Barcelona"]["simulated_seats"]["Bloque izquierda sin PSC"] == 11
    assert left["Madrid"]["coalition_comparisons"][0]["delta"] == 0
    assert left["Barcelona"]["coalition_comparisons"][0]["delta"] == 2
    assert broad["Madrid"]["simulated_seats"]["Bloque amplio PSOE-SUMAR"] == 17
    assert broad["Barcelona"]["simulated_seats"]["Bloque amplio PSC-ECP-ERC-CUP"] == 23
    assert broad["Madrid"]["coalition_comparisons"][0]["delta"] == 1
    assert broad["Barcelona"]["coalition_comparisons"][0]["delta"] == 1
