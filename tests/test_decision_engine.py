import pytest
from src.decision_engine import coalition_result,apply_absolute_shift,Scenario,validate_scenario

def base():
    return ({"A":{"X":600,"Y":250,"Z":150},"B":{"X":500,"Y":300,"Z":200}},
            {"A":3,"B":3},{"A":1000,"B":1000},{},{})
def test_coalition_reallocates():
    v,s,valid,special,blank=base()
    r=coalition_result(v,s,valid,("X","Y"),special,blank)
    assert r["total_coalition"]==6
    assert r["delta"]==r["total_coalition"]-r["total_separate"]
def test_ambiguous_shift_rejected():
    with pytest.raises(ValueError,match="AMBIGUOUS_SCENARIO"):
        validate_scenario(Scenario("national_shift",party="X",shift_type="absolute_points",shift_value=2,territorial_distribution="unspecified"))
def test_uniform_shift_changes_votes_explicitly():
    assert apply_absolute_shift({"A":{"X":600,"Y":400}},"X",2,"uniform_by_province")["A"]["X"]==620
