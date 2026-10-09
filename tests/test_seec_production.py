from pathlib import Path

def test_seec_production_contract_is_canonical():
    text = Path("scripts/run_seec_production.py").read_text(encoding="utf-8")
    assert 'artifacts/data/cis_historical_2004_2023.csv' in text
    assert 'chains=4' in text
    assert 'total_draws<10000' in text
    assert 'diverging' in text
    assert 'r_hat' in text
    assert 'fail_closed' in text


def test_seec_production_diagnoses_latent_trajectory_and_fails_closed_on_nonfinite_values():
    text = Path("scripts/run_seec_production.py").read_text(encoding="utf-8")
    assert 'diagnostic_variables=["temporal_sigma","log_concentration","eta0","eta"]' in text
    assert 'np.isfinite(rhat_values).all()' in text
    assert 'np.isfinite(ess_bulk_values).all()' in text
    assert 'np.isfinite(ess_tail_values).all()' in text
    assert '"latent_eta_included":True' in text
