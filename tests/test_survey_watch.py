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


def test_watch_normalizes_canonical_poll_id_for_report_schema():
    from scripts.survey_watch import _report_record, _stable_poll_id
    canonical = {
        "poll_id": "source::2026-10-09::study",
        "publication_date": "2026-10-09",
        "parties": {"PSOE": 31.0},
    }
    normalized = _report_record(canonical)
    assert _stable_poll_id(canonical) == "source::2026-10-09::study"
    assert normalized["id"] == canonical["poll_id"]
    assert normalized["poll_id"] == canonical["poll_id"]
    assert normalized["parties"] == canonical["parties"]


def test_watch_quarantines_records_without_any_stable_id():
    from scripts.survey_watch import _stable_poll_id
    assert _stable_poll_id({"parties": {"PSOE": 31.0}}) is None
