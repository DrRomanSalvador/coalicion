#!/usr/bin/env python3
"""Fail-closed official 2023 audit; delegates to the canonical shared verifier."""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.neutral_audit import audit_canonical

MATRIX = ROOT / "artifacts/data/election_2023_canonical.json"
REPORT = ROOT / "artifacts/data/election_2023_audit.json"


def main() -> int:
    result = audit_canonical(MATRIX)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
