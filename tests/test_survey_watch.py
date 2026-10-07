from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]

def test_watch_contract_is_neutral_and_explicit():
    cfg=json.loads((ROOT/"config/survey_watch.json").read_text(encoding="utf-8"))
    assert cfg["daily_local_hour"] == 8
    assert cfg["source_policy"]["require_explicit_sources"] is True
    assert cfg["source_policy"]["no_unverified_poll_values"] is True
    assert cfg["comparison_policy"]["descriptive_only"] is True
    assert cfg["comparison_policy"]["recommendations"] is False
    assert cfg["comparison_policy"]["ranking_as_best_option"] is False
    assert cfg["comparison_policy"]["campaign_advice"] is False
    assert ["SUMAR","PODEMOS"] in cfg["scenario_sets"]
    assert ["SUMAR","PSOE"] in cfg["scenario_sets"]
    assert ["SUMAR","PODEMOS","PSOE"] in cfg["scenario_sets"]

def test_watch_script_exists():
    assert (ROOT/"scripts/survey_watch.py").is_file()
    assert (ROOT/".github/workflows/daily_survey_watch.yml").is_file()
