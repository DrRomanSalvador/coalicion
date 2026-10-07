import pytest
from src.decision import Scenario,validate_scenario,apply_absolute_shift

def test_ambiguous_shift_rejected():
    with pytest.raises(ValueError,match="AMBIGUOUS_SCENARIO"):
        validate_scenario(Scenario("national_shift",party="X",shift_type="absolute_points",shift_value=2,territorial_distribution="unspecified"))

def test_uniform_shift_changes_votes_explicitly():
    assert apply_absolute_shift({"A":{"X":600,"Y":400}},"X",2,"uniform_by_province")["A"]["X"]==620
