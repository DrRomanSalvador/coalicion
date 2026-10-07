from src.coalition import coalition_decision

def test_coalition_is_recomputed_by_constituency():
    r=coalition_decision(
        {"A":{"P1":600,"P2":250,"P3":150}},
        {"A":3},
        {"A":0},
        ("P2","P3"),
    )
    assert r["separate_seats"] == 1
    assert r["coalition_seats"] == 1
    assert r["benefit"] == 0
    assert r["all_constituencies"] == [{"constituency":"A","separate":1,"coalition":1,"delta":0}]

def test_affected_constituencies_are_exposed():
    r=coalition_decision(
        {"A":{"P1":400,"P2":300,"P3":250}},
        {"A":3},
        {"A":0},
        ("P2","P3"),
    )
    assert r["decisive_constituencies"]
    assert r["coalition"]=="P2+P3"
