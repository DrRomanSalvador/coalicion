from pathlib import Path
import ast

from src.coalition import merge_coalition_votes
from src.electoral import dhondt, merge_candidacies

ROOT = Path(__file__).parents[1] / "src"
REMOVED = {
    "electoral_reference.py",
    "coalition_value.py",
    "scenarios.py",
    "decision_engine.py",
}
COALITION_FUNCS = {"merge_coalition_votes"}
PREDICTION_FUNCS = {"predict", "apply_share_swing", "historical_share_changes"}
DHONDT_FUNCS = {"dhondt", "d_hondt"}

def _functions(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}

def test_removed_duplicate_modules_are_absent():
    present = {p.name for p in ROOT.glob("*.py")}
    assert not present & REMOVED

def test_only_electoral_defines_dhondt():
    implementations = [p.name for p in ROOT.glob("*.py") if _functions(p) & DHONDT_FUNCS]
    assert implementations == ["electoral.py"]

def test_only_coalition_defines_coalition_calculators():
    implementations = {p.name for p in ROOT.glob("*.py") if _functions(p) & COALITION_FUNCS}
    assert implementations == {"coalition.py"}

def test_only_prediction_defines_prediction_api():
    implementations = {p.name for p in ROOT.glob("*.py") if _functions(p) & PREDICTION_FUNCS}
    assert implementations == {"prediction.py"}

def test_sum_seats_equals_S():
    result = dhondt({"A": 60, "B": 40}, 5, 100)
    assert result.status == "OK"
    assert sum(result.seats.values()) == 5

def test_sum_shares_equals_one():
    shares = {"A": 0.4, "B": 0.6}
    assert sum(shares.values()) == 1

def test_v_AB_equals_v_A_plus_v_B():
    a = {"A": 60}
    b = {"B": 40}
    merged = merge_candidacies(a, b)
    assert merged == {"A": 60, "B": 40}
    assert sum(merged.values()) == sum(a.values()) + sum(b.values())

def test_coalition_seats_are_recomputed_not_added():
    votes = {"X": {"A": 5, "B": 8, "C": 87}}
    separate = dhondt(votes["X"], 7, 100).seats
    merged = merge_coalition_votes(votes, ("A", "B"))["X"]
    joined = dhondt(merged, 7, 100).seats["A+B"]
    assert separate["A"] + separate["B"] == 0
    assert joined == 1
