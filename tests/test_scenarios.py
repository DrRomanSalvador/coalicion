import pytest
from src.scenarios import compare_scenarios


def test_coalition_reallocates_instead_of_summing_seats():
    votes={"X":{"A":60,"B":25,"C":15}}
    out=compare_scenarios(votes,{"X":3},{"X":100},{"X":0},[("A","B")])
    assert sum(out["SEPARADOS"].values())==3
    assert sum(out["A+B"].values())==3
    assert out["A+B"]["A+B"]>=out["SEPARADOS"].get("A",0)+out["SEPARADOS"].get("B",0)


def test_special_constituency_is_not_run_through_dhondt():
    votes={"Ceuta":{"A":50,"B":40},"X":{"A":60,"B":40}}
    seats={"Ceuta":1,"X":1}
    valid={"Ceuta":90,"X":100}
    blank={"Ceuta":0,"X":0}
    out=compare_scenarios(votes,seats,valid,blank,[("A","B")],{"Ceuta":"Ceuta"})
    assert out["SEPARADOS"]["A"]==2


def test_ambiguous_or_missing_coalition_party_blocks():
    with pytest.raises(ValueError):
        compare_scenarios({"X":{"A":100}}, {"X":1}, {"X":100}, {"X":0}, [("A","B")])
