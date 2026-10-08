from pathlib import Path
from src.cis_history import load

def test_cis_manifest_and_runner_contract():
    assert Path('ci_evidence/cis_historical_manifest.json').is_file()
    assert len(load()) == 110
    text = Path('scripts/run_seec_production.py').read_text(encoding='utf-8')
    assert 'SURVEY = {' not in text
    assert 'load_cis' in text
