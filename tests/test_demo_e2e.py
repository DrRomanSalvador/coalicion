import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_demo_e2e_uses_materialized_2023_data_and_recomputes_coalition():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/demo_e2e.py")],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    result = json.loads(proc.stdout)
    assert result["demo_status"] == "PASS"
    assert result["election"] == 2023
    assert result["constituency"] == "Madrid"
    assert result["data_status"] == "OFFICIAL_PRIMARY_RECONCILED"
    assert result["official_certification"] == "NOT_EXTERNALLY_CERTIFIED"
    assert result["seats_separate"] + result["delta_seats"] == result["seats_coalition"]
    assert result["canonical_engine"] == "src.coalition"
