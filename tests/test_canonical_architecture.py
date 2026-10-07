from pathlib import Path

ROOT = Path(__file__).parents[1]
SRC = ROOT / "src"

def test_canonical_modules_exist():
    for name in ("data.py", "electoral.py", "prediction.py", "coalition.py", "uncertainty.py", "decision.py"):
        assert (SRC / name).is_file(), name

def test_obsolete_duplicate_modules_are_absent():
    for name in (
        "data_pipeline.py",
        "prediction_engine.py",
        "coalition_value.py",
        "coalition_decision.py",
        "coalition_decision_engine.py",
        "scenarios.py",
        "decision_engine.py",
    ):
        assert not (SRC / name).exists(), name
