from scripts.run_seec_production import SURVEY

def test_seec_production_survey_is_complete():
    assert len(SURVEY) >= 5
    assert abs(sum(SURVEY.values()) - 100.0) < 1e-9
