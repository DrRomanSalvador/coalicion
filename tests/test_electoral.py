import pytest
from src.electoral import allocate,ceuta_melilla,dhondt,merge_candidacies,valid_votes

def test_blank_votes_are_valid():
    assert valid_votes({"A":970,"B":20},10)==1000
    assert dhondt({"A":970,"B":20},1,1000,10).seats["A"]==1
def test_threshold_exact():
    assert dhondt({"A":97,"B":3},1,100).status=="OK"
def test_below_threshold():
    assert dhondt({"A":96,"B":2,"C":2},1,100).seats["C"]==0
def test_quotient_tie_uses_votes():
    assert dhondt({"A":100,"B":50},2,150).seats=={"A":2,"B":0}
def test_absolute_tie_blocks_not_lexicographic():
    r=dhondt({"ZZ":100,"AA":100},1,200)
    assert r.status=="EMPATE_ABSOLUTO_PENDIENTE" and r.tie==("AA","ZZ")
def test_ceuta_majority():
    assert ceuta_melilla({"A":40,"B":35},100).seats["A"]==1
def test_ceuta_tie_blocks():
    assert ceuta_melilla({"A":50,"B":50},100).status=="EMPATE_MAYORIA_PENDIENTE"
def test_special_one_seat():
    with pytest.raises(ValueError): allocate({"A":10},2,10,"Ceuta")
def test_incomplete_matrix():
    with pytest.raises(ValueError): dhondt({"A":60},1,100)
def test_merge_before_allocation():
    assert merge_candidacies({"A":40},{"A":30,"B":20})=={"A":70,"B":20}
