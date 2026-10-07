import pytest
from src.coalition import compare_scenarios,coalition_result

def base():
    return ({"A":{"X":600,"Y":250,"Z":150},"B":{"X":500,"Y":300,"Z":200}},
            {"A":3,"B":3},{"A":1000,"B":1000},{},{})
def test_coalition_reallocates():
    v,s,valid,special,blank=base(); r=coalition_result(v,s,valid,("X","Y"),special,blank)
    assert r["total_coalition"]==6 and r["delta"]==r["total_coalition"]-r["total_separate"]

def test_scenario_conserves_seats():
    v,s,valid,special,blank=base(); out=compare_scenarios(v,s,valid,blank,[("X","Y")],special)
    assert sum(out["SEPARADOS"].values())==6 and sum(out["X+Y"].values())==6

def test_coalition_is_not_sum_of_seats():
    out=compare_scenarios({"X":{"A":60,"B":25,"C":15}},{"X":3},{"X":100},{"X":0},[("A","B")])
    assert out["A+B"]["A+B"]>=out["SEPARADOS"].get("A",0)+out["SEPARADOS"].get("B",0)

def test_special_constituency():
    out=compare_scenarios({"Ceuta":{"A":50,"B":40},"X":{"A":60,"B":40}},{"Ceuta":1,"X":1},{"Ceuta":90,"X":100},{"Ceuta":0,"X":0},[("A","B")],{"Ceuta":"Ceuta"})
    assert out["SEPARADOS"]["A"]==2

def test_missing_party_blocks():
    with pytest.raises(ValueError):
        compare_scenarios({"X":{"A":100}},{"X":1},{"X":100},{"X":0},[("A","B")])
