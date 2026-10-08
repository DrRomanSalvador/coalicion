from scripts.run_seec_production import SURVEY, SURVEY_SOURCE_SUM

def test_seec_production_survey_is_canonical_and_not_renormalized():
    assert len(SURVEY) == 12
    assert abs(SURVEY_SOURCE_SUM - 96.5) < 1e-9
    assert abs(sum(SURVEY.values()) - SURVEY_SOURCE_SUM) < 1e-9
