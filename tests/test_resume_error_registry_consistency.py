from pathlib import Path
import json

from src.error_registry import validate_code


def test_all_persisted_blockers_are_registered():
    state = json.loads(Path("docs/COLMENA_STATE.json").read_text(encoding="utf-8"))
    for item in state.get("blocking_errors", []):
        validate_code(item["id"])
