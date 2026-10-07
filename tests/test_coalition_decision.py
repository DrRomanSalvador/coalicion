from src.coalition import coalition_decision

def test_coalition_is_recomputed_by_constituency():
    r=coalition_decision(
        {"A":{"P1":600,"P2":250,"P3":150}},
        {"A":3},
        {"A":0},
        ("P2","P3"),
    )
    assert r["total_separate"]==1
    assert r["total_coalition"]==1
    assert r["delta"]==0

def test_affected_constituencies_are_exposed():
    r=coalition_decision(
        {"A":{"P1":400,"P2":300,"P3":250}},
        {"A":3},
        {"A":0},
        ("P2","P3"),
    )
    assert "affected_constituencies" in r
    assert r["coalition"]=="P2+P3"
