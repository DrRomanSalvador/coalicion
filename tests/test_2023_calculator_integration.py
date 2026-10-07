import json
import subprocess
import sys
from pathlib import Path

import pytest


CANONICAL = Path("artifacts/data/election_2023_canonical.json")


def test_2023_matrix_integration_real_data():
    if not CANONICAL.exists():
        pytest.fail("MATRIX_NOT_AVAILABLE: artifacts/data/election_2023_canonical.json")
    output = Path("artifacts/data/test_coalition_calculator_integration.json")
    subprocess.run(
        [
            sys.executable,
            "scripts/integrate_2023_calculator.py",
            "--canonical",
            str(CANONICAL),
            "--output",
            str(output),
        ],
        check=True,
    )
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["source_tier"] == "SECONDARY_REPLICA_VERIFIED"
    assert data["validation"]["constituencies"] == 52
    assert data["validation"]["seats"] == 350
    assert data["validation"]["candidate_votes"] == 24_487_414
    assert data["validation"]["valid_votes"] == 24_688_087
    assert sum(data["baseline_2023"]["national_seats"].values()) == 350
    assert data["calculator"]["invented_votes"] is False


def test_2023_matrix_missing_fails_closed(tmp_path):
    missing = tmp_path / "missing.json"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/integrate_2023_calculator.py",
            "--canonical",
            str(missing),
            "--output",
            str(tmp_path / "out.json"),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "MATRIX_NOT_AVAILABLE" in result.stderr or "MATRIX_NOT_AVAILABLE" in result.stdout


def test_constituency_aliases_resolve_to_canonical():
    from scripts.integrate_2023_calculator import canonical_constituency

    known = {"Valencia/València", "Balears, Illes", "Castellón/Castelló", "Araba/Álava"}
    assert canonical_constituency("Valencia", known) == "Valencia/València"
    assert canonical_constituency("València", known) == "Valencia/València"
    assert canonical_constituency("País Valencià", known) == "Valencia/València"
    assert canonical_constituency("Baleares", known) == "Balears, Illes"
    assert canonical_constituency("Castelló", known) == "Castellón/Castelló"
    assert canonical_constituency("Álava", known) == "Araba/Álava"
