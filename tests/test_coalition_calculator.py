import pytest

from src.coalition_decision_engine import CoalitionDecisionEngine, CoalitionScenario


def test_central_scenario_must_be_explicit():
    engine = CoalitionDecisionEngine({"A": 3}, {"A": 0})
    scenarios = [
        CoalitionScenario("pessimistic", {"A": {"P1": 4, "P2": 1}}),
        CoalitionScenario("optimistic", {"A": {"P1": 4, "P2": 1}}),
    ]
    with pytest.raises(ValueError, match="central"):
        engine.analyze_coalition(("P1", "P2"), scenarios)


def test_separate_result_uses_all_candidates():
    engine = CoalitionDecisionEngine({"A": 3}, {"A": 0})
    result = engine.analyze_coalition(
        ("P1", "P2"),
        [CoalitionScenario("central", {"A": {"P1": 100, "P2": 100, "P3": 500}})],
    )
    # P1 and P2 receive seats against P3; neither is calculated in isolation.
    assert result["separate_seats"] == 0
    assert result["coalition_seats"] == 1
    assert result["benefit"] == 1


def test_all_constituencies_are_analyzed():
    engine = CoalitionDecisionEngine({"A": 3, "B": 3}, {"A": 0, "B": 0})
    result = engine.analyze_coalition(
        ("P1", "P2"),
        [CoalitionScenario("central", {
            "A": {"P1": 100, "P2": 100, "P3": 500},
            "B": {"P1": 100, "P2": 100, "P3": 500},
        })],
    )
    assert len(result["decisive_constituencies"]) == 2
