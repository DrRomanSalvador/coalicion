import pytest
from src.coalition_decision_engine import CoalitionDecisionEngine, CoalitionScenario


def test_central_scenario_must_be_explicit():
    engine = CoalitionDecisionEngine({"A": 350}, {"A": 0})
    scenarios = [
        CoalitionScenario("pessimistic", {"A": {"P1": 401, "P2": 199}}),
        CoalitionScenario("optimistic", {"A": {"P1": 401, "P2": 199}}),
    ]
    with pytest.raises(ValueError, match="central"):
        engine.analyze_coalition(("P1", "P2"), scenarios)


def test_separate_result_uses_all_candidates():
    engine = CoalitionDecisionEngine({"A": 350}, {"A": 0})
    result = engine.analyze_coalition(
        ("P1", "P2"),
        [CoalitionScenario("central", {"A": {"P1": 600, "P2": 20, "P3": 380}})],
    )
    assert result["separate_seats"] < 350
    assert result["coalition_seats"] >= result["separate_seats"]


def test_all_constituencies_are_analyzed():
    engine = CoalitionDecisionEngine({"A": 175, "B": 175}, {"A": 0, "B": 0})
    result = engine.analyze_coalition(
        ("P1", "P2"),
        [CoalitionScenario("central", {
            "A": {"P1": 600, "P2": 20, "P3": 380},
            "B": {"P1": 500, "P2": 301, "P3": 199},
        })],
    )
    assert len(result["decisive_constituencies"]) == 2
