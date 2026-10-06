import importlib.util
import unittest
from fractions import Fraction

from src.electoral import dhondt
from src.marginality import marginal_seat


class HardeningTests(unittest.TestCase):
    def test_dhondt_absolute_tie_blocks(self):
        result = dhondt({"A": 100, "B": 100}, 1, 200, 0)
        self.assertEqual(result.status, "EMPATE_ABSOLUTO_PENDIENTE")

    def test_dhondt_equal_quotient_but_more_total_votes_resolves(self):
        result = dhondt({"A": 200, "B": 100}, 2, 300, 0)
        self.assertEqual(result.status, "OK")
        self.assertEqual(result.seats["A"], 2)

    def test_marginality_uses_exact_fraction(self):
        result = marginal_seat({"A": 100, "B": 90}, 2, 0, "")
        self.assertIsInstance(result["last_quotient"], Fraction)

    def test_exhaustive_resolver_never_averages(self):
        spec = importlib.util.spec_from_file_location(
            "exhaustive", "scripts/exhaustive_data_acquisition.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result = module.resolve([
            {"tier": "PRIMARY", "authority": "MINISTERIO_INTERIOR", "source_id": "P", "value": 100},
            {"tier": "SECONDARY", "authority": "SECONDARY", "source_id": "S", "value": 102},
        ])
        self.assertEqual(result["status"], "RESOLVED_PRIMARY")
        self.assertEqual(result["value"], 100)


if __name__ == "__main__":
    unittest.main()
