from src.electoral import dhondt, ceuta_melilla, merge_candidacies

def test_dhondt_simple():
    r = dhondt({"A": 100, "B": 60}, 3, 160)
    assert r.status == "OK"
    assert r.seats == {"A": 2, "B": 1}

def test_three_percent_boundary():
    r = dhondt({"A": 100, "B": 97, "C": 3}, 2, 100)
    assert r.status == "OK"

def test_ceuta_majority_not_dhondt():
    r = ceuta_melilla({"A": 40, "B": 35, "C": 25})
    assert r.seats == {"A": 1, "B": 0, "C": 0}

def test_ceuta_absolute_tie_is_blocked():
    r = ceuta_melilla({"A": 50, "B": 50})
    assert r.status == "EMPATE_MAYORIA_PENDIENTE"

def test_fusion_before_allocation():
    merged = merge_candidacies({"A": 40}, {"A": 30, "B": 20})
    assert merged == {"A": 70, "B": 20}
    r = dhondt(merged, 1, 90)
    assert r.seats["A"] == 1
