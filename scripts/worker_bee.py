#!/usr/bin/env python3
"""Generic deterministic worker for REINA-SEEC."""
from __future__ import annotations
import subprocess, sys

if len(sys.argv) < 2:
    print("FAIL_CLOSED: no task supplied", file=sys.stderr)
    raise SystemExit(2)
try:
    result = subprocess.run(sys.argv[1:], text=True)
except Exception as exc:
    print(f"FAIL_CLOSED: {type(exc).__name__}: {exc}", file=sys.stderr)
    raise SystemExit(1)
raise SystemExit(result.returncode)
