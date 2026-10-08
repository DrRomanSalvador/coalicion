from pathlib import Path
from src.cis_history import load

def test_cis_manifest_and_runner_contract():
    assert Path('ci_evidence/cis_historical_manifest.json').is_file()
    assert len(load()) == 110
    text = Path('scripts/run_seec_production.py').read_text(encoding='utf-8')
    assert 'SURVEY = {' not in text
    assert 'load_cis' in text

import pytest

def test_oos_excludes_null_and_aggregate_rows(tmp_path):
    from src.oos_pipeline import _official
    p = tmp_path / "official.csv"
    p.write_text(
        "election,partido,votos\n2023,PP,40\n2023,PSOE,50\n"
        "2023,Votos en blanco,10\n2023,Votos nulos,5\n2023,Total,105\n",
        encoding="utf-8",
    )
    actuals = _official(p)
    assert actuals[("2023J", "PP")] == pytest.approx(40.0)
    assert actuals[("2023J", "PSOE")] == pytest.approx(50.0)
