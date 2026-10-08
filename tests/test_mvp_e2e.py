import json
from pathlib import Path

from src.email.newsletter import build_newsletter
from src.pipeline.full_election import run_full_election


ROOT = Path(__file__).resolve().parents[1]


def test_current_survey_registry_has_ten_rows_and_fail_closed_metadata():
    data = json.loads(
        (ROOT / "data/surveys/current_2026/current_national.json").read_text(encoding="utf-8")
    )
    assert data["count"] >= 10
    assert len(data["surveys"]) >= 10
    assert data["policy"]["fail_closed"] is True
    assert data["policy"]["primary_required_for_official_claims"] is True


def test_newsletter_is_generated_from_materialized_surveys():
    html = build_newsletter()
    assert "SALA DE SITUACIÓN" in html
    assert "COALICIÓN" in html
    assert "Encuestadora" in html


def test_e2e_blocks_fake_national_to_territorial_conversion():
    result = run_full_election(
        poll={"id": "current_2026_demo"},
        territorial_votes=None,
        seats=None,
        blank=None,
    )
    assert result["status"] == "BLOCKED"
    assert result["policy"]["national_to_territorial_inference"] is False
