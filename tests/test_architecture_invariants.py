from fractions import Fraction
from src.data import merge_votes,validate_share_vector
from src.electoral import dhondt
from src.coalition import merge_coalition_votes

def test_sum_shares_is_one():
    validate_share_vector({"A":0.4,"B":0.6})

def test_seats_sum_to_S():
    r=dhondt({"A":60,"B":40},5,100)
    assert r.status=="OK"
    assert sum(r.seats.values())==5

def test_v_AB_equals_v_A_plus_v_B():
    a={"A":60}; b={"B":40}
    assert merge_votes(a,b)=={"A":60,"B":40}

def test_coalition_seats_are_recomputed_not_added():
    votes={"X":{"A":10,"B":15,"C":75}}
    separate=dhondt(votes["X"],3,100).seats
    merged=merge_coalition_votes(votes,("A","B"))["X"]
    joined=dhondt(merged,3,100).seats["A+B"]
    assert joined != separate["A"]+separate["B"]
