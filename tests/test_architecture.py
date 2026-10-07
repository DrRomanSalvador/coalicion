from pathlib import Path
import ast

ROOT=Path(__file__).parents[1]/"src"
CANONICAL={"electoral.py","data.py","prediction.py","coalition.py","uncertainty.py","decision.py","__init__.py"}
DUPLICATES={"electoral_reference.py","coalition_value.py","scenarios.py","decision_engine.py","bias_filter.py","calibration.py","poll_error.py","context_corrections.py","prediction_engine.py","coalition_decision.py","coalition_decision_engine.py"}

def test_only_canonical_domain_modules_exist():
    present={p.name for p in ROOT.glob("*.py")}
    assert not present & DUPLICATES, f"duplicidades detectadas: {sorted(present & DUPLICATES)}"

def test_dhondt_has_one_implementation():
    implementations=[]
    for path in ROOT.glob("*.py"):
        tree=ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name.lower() in {"dhondt","d_hondt"}:
                implementations.append(path.name)
    assert implementations==["electoral.py"], implementations

def test_domain_api_has_no_parallel_engine_names():
    present={p.stem for p in ROOT.glob("*.py")}
    assert not {"prediction_engine","coalition_decision","coalition_decision_engine","decision_engine"} & present

def test_dhondt_is_only_called_by_domain_modules():
    # This test guards against a second allocator being introduced under a new name.
    text="\n".join(p.read_text(encoding="utf-8") for p in ROOT.glob("*.py"))
    assert text.count("def dhondt(")==1
