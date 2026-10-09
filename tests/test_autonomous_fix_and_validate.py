"""Regression tests for canonical historical OOS gate inputs."""
import json
from pathlib import Path

from scripts import autonomous_fix_and_validate as validation


def test_oos_gate_uses_materialized_cis_history_not_empty_legacy_csv():
    source = Path(validation.__file__).read_text(encoding="utf-8")
    assert 'ROOT / "artifacts" / "data" / "cis_historical_2004_2023.csv"' in source
    assert 'ROOT / "data" / "encuestas_historicas_2004_2023.csv"' not in source
    assert "scripts/complete_historical_calibration.py" in source


def test_oos_calibration_gate_requires_real_coverage_and_all_leakage_checks(tmp_path, monkeypatch):
    source = Path(validation.__file__).read_text(encoding="utf-8")
    assert 'checks.get("all_test_elections_use_only_prior_elections")' in source
    assert 'checks.get("evaluated_election_excluded_from_training")' in source
    assert 'evidence.get("coverage_gate", {}).get("passed")' in source


def test_full_backtest_defaults_to_canonical_cis_history():
    source = Path(__file__).resolve().parents[1] / "scripts" / "run_full_backtest.py"
    assert 'default="artifacts/data/cis_historical_2004_2023.csv"' in source.read_text(encoding="utf-8")


def test_baseline_is_delegated_once_to_canonical_full_backtest():
    source = Path(validation.__file__).read_text(encoding="utf-8")
    assert "obsolete secondary-replica staging file" in source
    assert "Delegated once to scripts/run_full_backtest.py" in source
    assert '["backtest_2023_baseline.py"]' not in source
