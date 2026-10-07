from src.coalition_decision_engine import CoalitionDecisionEngine, CoalitionScenario

def scenario(votes, name="central", weight=1):
    return CoalitionScenario(name, votes, weight)

def engine():
    return CoalitionDecisionEngine({"A": 3, "B": 3}, {"A": 0, "B": 0})

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
        "A":{"P1":500,"P2":260,"P3":240},
        "B":{"P1":500,"P2":260,"P3":240}})])
    assert r["separate_seats"] == 2
    assert r["coalition_seats"] == 2
    assert r["benefit"] == 0

def test_weighted_risk_is_not_three_scenario_arithmetic():
    r = engine().analyze_coalition(("P2","P3"), [
        scenario({"A":{"P1":400,"P2":310,"P3":290},
                  "B":{"P1":400,"P2":310,"P3":290}}, weight=3),
        scenario({"A":{"P1":500,"P2":260,"P3":240},
                  "B":{"P1":500,"P2":260,"P3":240}}, "no_gain", 1)])
    assert r["risk"]["probability_non_improvement"] == 0.25
    assert r["robustness"]["weighted_mean_delta"] > 0

def test_decisive_constituencies_are_exposed():
    r = engine().analyze_coalition(("P2","P3"), [scenario({
        "A":{"P1":400,"P2":300,"P3":300},
        "B":{"P1":700,"P2":150,"P3":150}})])
    assert r["decisive_constituencies"]
    assert r["decisive_constituencies"][0]["constituency"] == "A"

def test_no_arbitrary_shift_is_embedded():
    assert not hasattr(engine(), "run_scenario")
