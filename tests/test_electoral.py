import pytest

from src.electoral import allocate, ceuta_melilla, dhondt, merge_candidacies


def test_dhondt_simple():
    r = dhondt({"A": 100, "B": 60}, 3, 160)
    assert r.status == "OK"
    assert r.seats == {"A": 2, "B": 1}


def test_three_percent_boundary():
    r = dhondt({"A": 97, "B": 3}, 2, 100)
    assert r.status == "OK"


def test_exact_three_percent_is_eligible():
    r = dhondt({"A": 97, "B": 3}, 1, 100)
    assert r.status == "OK"
    assert r.seats["B"] == 0


def test_below_three_percent_is_excluded():
    r = dhondt({"A": 96, "B": 4, "C": 2}, 1, 102)
    assert r.seats["C"] == 0


def test_tie_quotient_uses_total_votes():
    r = dhondt({"A": 100, "B": 50}, 2, 150)
    assert r.status == "OK"
    assert r.seats == {"A": 2, "B": 0}


def test_absolute_quotient_tie_is_blocked():
    r = dhondt({"A": 100, "B": 100}, 1, 200)
    assert r.status == "EMPATE_ABSOLUTO_PENDIENTE"
    assert r.tie == ("A", "B")


def test_incomplete_vote_matrix_is_blocked():
    with pytest.raises(ValueError, match="sumar exactamente"):
        dhondt({"A": 60}, 1, 100)


def test_negative_votes_rejected():
    with pytest.raises(ValueError):
        dhondt({"A": -1, "B": 101}, 1, 100)


def test_zero_valid_votes_rejected():
    with pytest.raises(ValueError):
        dhondt({"A": 0}, 1, 0)


def test_votes_cannot_exceed_valid_votes():
    with pytest.raises(ValueError):
        dhondt({"A": 101}, 1, 100)


def test_bool_votes_rejected():
    with pytest.raises(ValueError):
        dhondt({"A": True, "B": 99}, 1, 100)


def test_invalid_party_name_rejected():
    with pytest.raises(ValueError):
        dhondt({"": 100}, 1, 100)


def test_ceuta_majority_not_dhondt():
    r = ceuta_melilla({"A": 40, "B": 35, "C": 25}, 100)
    assert r.seats == {"A": 1, "B": 0, "C": 0}


def test_ceuta_absolute_tie_is_blocked():
    r = ceuta_melilla({"A": 50, "B": 50}, 100)
    assert r.status == "EMPATE_MAYORIA_PENDIENTE"


def test_ceuta_tie_is_not_resolved_by_party_name():
    r = ceuta_melilla({"ZZ": 50, "AA": 50}, 100)
    assert r.status == "EMPATE_MAYORIA_PENDIENTE"


def test_melilla_majority():
    r = ceuta_melilla({"A": 1, "B": 2}, 3)
    assert r.seats == {"A": 0, "B": 1}


def test_special_constituency_requires_one_seat():
    with pytest.raises(ValueError):
        allocate({"A": 10}, 2, 10, "Ceuta")


def test_fusion_before_allocation():
    merged = merge_candidacies({"A": 40}, {"A": 30, "B": 20})
    assert merged == {"A": 70, "B": 20}
    r = dhondt(merged, 1, 90)
    assert r.seats["A"] == 1


def test_fusion_is_vote_level_not_seat_level():
    merged = merge_candidacies({"A": 30, "B": 20}, {"A": 25, "C": 15})
    assert merged == {"A": 55, "B": 20, "C": 15}


def test_all_allocated_seats_are_conserved():
    r = dhondt({"A": 100, "B": 80, "C": 40}, 5, 220)
    assert sum(r.seats.values()) == 5


def test_dhondt_is_deterministic():
    votes = {"A": 100, "B": 80, "C": 40}
    assert dhondt(votes, 5, 220) == dhondt(votes, 5, 220)


def test_zero_vote_party_cannot_qualify():
    r = dhondt({"A": 100, "B": 0}, 1, 100)
    assert r.seats["B"] == 0


def test_missing_candidate_capacity_reports_failure():
    r = dhondt({}, 1, 100)
    assert r.status == "INSUFICIENTES_CANDIDATURAS"
