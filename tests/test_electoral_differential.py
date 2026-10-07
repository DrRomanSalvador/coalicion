import random
import pytest

from src.electoral import dhondt
from src.electoral_reference import allocate_reference


def _case(seed):
    rng=random.Random(seed)
    parties=[f"P{i}" for i in range(rng.randint(2,8))]
    votes={p:rng.randint(0,5000) for p in parties}
    if sum(votes.values()) == 0:
        votes[parties[0]]=1
    blank=rng.randint(0,300)
    valid=sum(votes.values())+blank
    seats=rng.randint(1,12)
    return votes,seats,valid,blank


def test_reference_matches_production_on_adversarial_edges():
    edges=[
        ({"A":100,"B":50},2,150,0),
        ({"A":97,"B":3},1,100,0),
        ({"A":96,"B":2,"C":2},1,100,0),
        ({"A":970,"B":20},1,1000,10),
        ({"A":1,"B":1,"C":100},7,102,0),
    ]
    for votes,seats,valid,blank in edges:
        assert dhondt(votes,seats,valid,blank).seats == allocate_reference(votes,seats,valid,blank)


def test_reference_matches_production_for_reproducible_random_cases():
    for seed in range(2000):
        votes,seats,valid,blank=_case(seed)
        a=dhondt(votes,seats,valid,blank)
        try:
            b=allocate_reference(votes,seats,valid,blank)
        except RuntimeError as exc:
            if a.status == "OK":
                pytest.fail(
                    f"oracle mismatch seed={seed}: production accepted but reference blocked: "
                    f"{votes=}, {seats=}, {valid=}, {blank=}, error={exc}"
                )
        else:
            assert a.status == "OK"
            assert a.seats==b


def test_reference_also_blocks_absolute_tie():
    with pytest.raises(RuntimeError, match="EMPATE_ABSOLUTO_PENDIENTE"):
        allocate_reference({"AA":100,"ZZ":100},1,200)
