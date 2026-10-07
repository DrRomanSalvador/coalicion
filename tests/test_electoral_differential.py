from fractions import Fraction
from src.electoral import dhondt

def test_seat_conservation():
    for votes,seats,valid,blank in [
        ({"A":100,"B":50},2,150,0),
        ({"A":97,"B":3},1,100,0),
        ({"A":970,"B":20},1,1000,10),
    ]:
        result=dhondt(votes,seats,valid,blank)
        assert result.status=="OK"
        assert sum(result.seats.values())==seats

def test_threshold_and_exact_quotients_remain_deterministic():
    assert dhondt({"A":97,"B":3},1,100).seats=={"A":1,"B":0}
    assert dhondt({"A":100,"B":50},2,150).seats=={"A":2,"B":0}
