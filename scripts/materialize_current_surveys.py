#!/usr/bin/env python3
"""Materialize the canonical current-survey registry using the shared data boundary."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data import normalize_registry

SOURCE = ROOT / "data/surveys/current_2026/current_national.json"
DESTINATION = ROOT / "artifacts/surveys/current_2026_normalized.json"


def main() -> int:
    result = normalize_registry(SOURCE)
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    # Atomic replacement prevents consumers from reading a partial JSON artifact.
    fd, temporary = tempfile.mkstemp(
        prefix=f".{DESTINATION.name}.", suffix=".tmp", dir=DESTINATION.parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, DESTINATION)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise
    print(result["normalized_hash"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
