from pathlib import Path

def test_seec_production_contract_is_canonical():
    text = Path("scripts/run_seec_production.py").read_text(encoding="utf-8")
    assert 'artifacts/data/cis_historical_2004_2023.csv' in text
    assert 'chains=4' in text
    assert 'total_draws<10000' in text
    assert 'diverging' in text
    assert 'r_hat' in text
    assert 'fail_closed' in text
