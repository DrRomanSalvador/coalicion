import unittest

from src.coalition_decision_engine import CoalitionScenario
from src.product_layer import (
    decide_coalition, rank_coalitions, coalition_alert,
    shock_scenario, generate_leader_report, compare_scenarios,
    analyze_value, audit_decision,
)


class ProductLayerTests(unittest.TestCase):
    def setUp(self):
        self.seats = {"A": 2, "B": 2}
        self.votes = {
            "A": {"P1": 50, "P2": 30, "P3": 20},
            "B": {"P1": 40, "P2": 20, "P3": 40},
        }
        self.scenarios = [
            CoalitionScenario("central", self.votes, 1.0, ("test",)),
            CoalitionScenario("optimistic", self.votes, 1.0, ("test",)),
        ]

    def test_decide(self):
        r = decide_coalition("P1", "P2", self.scenarios, self.seats)
        self.assertEqual(r["product"]["function"], "decide")
        self.assertEqual(r["product"]["decision"]["seat_delta"], 1)
        self.assertIn("technical", r)

    def test_ranking(self):
        r = rank_coalitions(["P1", "P2", "P3"], self.scenarios, self.seats)
        self.assertEqual(r["product"]["function"], "ranking")
        self.assertEqual(len(r["product"]["decision"]["ranking"]), 4)

    def test_alert(self):
        r = coalition_alert("P1", "P2", self.scenarios, self.seats)
        self.assertEqual(r["product"]["function"], "alert")
        self.assertEqual(r["product"]["decision"]["net_seat_delta"], 1)

    def test_shock(self):
        r = shock_scenario(self.votes, self.seats, "P1", 10)
        self.assertEqual(r["product"]["function"], "shock")
        self.assertIn("seat_change", r["product"]["decision"])

    def test_report(self):
        r = generate_leader_report("Lider", "P1", "P2", self.scenarios, self.seats)
        self.assertEqual(r["product"]["function"], "report")
        self.assertIn("# INFORME EJECUTIVO", r["product"]["markdown"])

    def test_scenarios(self):
        r = compare_scenarios("P1", "P2", self.scenarios, self.seats)
        self.assertEqual(r["product"]["function"], "scenarios")
        self.assertEqual(r["product"]["decision"]["worst_case"], 1)

    def test_value(self):
        r = analyze_value("P1", "P2", self.scenarios, self.seats)
        self.assertEqual(r["product"]["function"], "value")
        self.assertIn("votes_recovered", r["product"]["decision"])

    def test_audit_is_fail_closed(self):
        r = audit_decision()
        self.assertIn(r["product"]["status"], {"OK", "BLOCKED"})


if __name__ == "__main__":
    unittest.main()
