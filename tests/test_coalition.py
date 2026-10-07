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
        {"A":{"P1":600,"P2":250,"P3":150}},
        {"A":3},
        {"A":0},
        ("P2","P3"),
    )
    assert r["decisive_constituencies"]
    assert r["coalition"]=="P2+P3"


from src.coalition import CoalitionDecisionEngine, CoalitionScenario

def scenario(votes, name="central", weight=1):
    return CoalitionScenario(name, votes, weight)

def engine():
    return CoalitionDecisionEngine({"A": 3, "B": 347}, {"A": 0, "B": 0})

def test_exhaustive_generation_is_fail_closed():
    assert len(CoalitionDecisionEngine.generate_all_coalitions(["P1","P2","P3","P4"])) == 11
    try:
        CoalitionDecisionEngine.generate_all_coalitions([f"P{i}" for i in range(20)],
                                                        max_combinations=100)
    except ValueError as exc:
        assert "ESPACIO_EXCESIVO" in str(exc)
    else:
        raise AssertionError("debe fallar ante espacio combinatorio excesivo")

def test_recomputes_dhondt_instead_of_adding_seats():
    r = engine().analyze_coalition(("P2","P3"), [scenario({
        "A":{"P1":500,"P2":100,"P3":100},"B":{"P1":1000,"P2":1,"P3":1}})])
    assert r["separate_seats"] < r["coalition_seats"]
    assert r["benefit"] == r["coalition_seats"] - r["separate_seats"]

def test_weighted_risk_is_explicitly_weighted_not_probability_calibrated():
    r = engine().analyze_coalition(("P2","P3"), [
        scenario({"A":{"P1":500,"P2":100,"P3":100},"B":{"P1":1000,"P2":1,"P3":1}}, weight=3),
        scenario({"A":{"P1":500,"P2":260,"P3":100},"B":{"P1":1000,"P2":1,"P3":1}}, "no_gain", 1)])
    assert r["risk"]["weighted_non_improvement"] == 0.25
    assert "no son una probabilidad calibrada" in r["risk"]["weight_interpretation"]

def test_decisive_constituencies_are_exposed():
    e=CoalitionDecisionEngine({"A":350},{"A":0})
    r=e.analyze_coalition(("P2","P3"), [scenario({
        "A":{"P1":600,"P2":250,"P3":150}})])
    assert r["decisive_constituencies"]
    assert r["decisive_constituencies"][0]["constituency"] == "A"

def test_no_arbitrary_shift_is_embedded():
    assert not hasattr(engine(), "run_scenario")


def test_batch_output_is_mathematical_not_strategic():
    r = engine().analyze_all_coalitions(
        ["P1", "P2", "P3"],
        [scenario({
            "A": {"P1": 500, "P2": 260, "P3": 100},
            "B": {"P1": 1000, "P2": 1, "P3": 1},
        })],
        max_size=2,
    )
    assert "ranking" in r
    assert "recommendation" not in r
