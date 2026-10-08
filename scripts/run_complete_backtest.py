#!/usr/bin/env python3
"""Reproducible complete historical backtest.

Combines:
1. 2023 territorial baseline backtest (10,000 deterministic-seed simulations).
2. Strict expanding-window CIS OOS evaluation.
3. Historical probabilistic/calibration evidence when available.

The artifact is fail-closed: PASS is emitted only when every required block
passes its own contract. A valid execution with an unmet calibration gate is
materialized as NOT_CERTIFIED, never upgraded to PASS.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "artifacts/data/cis_historical_2004_2023.csv"
DEFAULT_OUTPUT = ROOT / "ci_evidence/backtest_complete_2004_2023.json"
DEFAULT_BASELINE_OUTPUT = ROOT / "ci_evidence/backtest_2023_baseline.json"
DEFAULT_OOS_OUTPUT = ROOT / "ci_evidence/oos_full_backtest.json"
DEFAULT_CAL_OUTPUT = ROOT / "ci_evidence/oos_calibration.json"


def run(cmd: list[str]) -> dict:
    p = subprocess.run(
        cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, check=False,
    )
    return {
        "command": cmd,
        "returncode": p.returncode,
        "output_tail": p.stdout[-12000:],
    }


def read_json(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = ap.parse_args()

    inp = args.input if args.input.is_absolute() else ROOT / args.input
    out = args.output if args.output.is_absolute() else ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)

    if not inp.is_file():
        payload = {
            "schema": "COALICION_COMPLETE_BACKTEST_V1",
            "status": "BLOCKED",
            "reason": f"missing canonical input: {inp}",
        }
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return 2

    commands = [
        [sys.executable, "scripts/backtest_2023_baseline.py"],
        [sys.executable, "scripts/run_full_oos.py",
         "--input", str(inp), "--output", str(DEFAULT_OOS_OUTPUT)],
        [sys.executable, "scripts/complete_historical_calibration.py",
         "--input", str(inp), "--output", str(DEFAULT_CAL_OUTPUT)],
    ]

    executions = []
    for cmd in commands:
        result = run(cmd)
        executions.append(result)
        if result["returncode"] != 0:
            payload = {
                "schema": "COALICION_COMPLETE_BACKTEST_V1",
                "status": "BLOCKED",
                "executed_at_utc": datetime.now(timezone.utc).isoformat(),
                "input": str(inp.relative_to(ROOT)),
                "input_sha256": hashlib.sha256(inp.read_bytes()).hexdigest(),
                "executions": executions,
                "evidence": {
                    "baseline": read_json(DEFAULT_BASELINE_OUTPUT),
                    "oos": read_json(DEFAULT_OOS_OUTPUT),
                    "calibration": read_json(DEFAULT_CAL_OUTPUT),
                },
            }
            out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            print(out.read_text(encoding="utf-8"))
            return result["returncode"]

    baseline = read_json(DEFAULT_BASELINE_OUTPUT)
    oos = read_json(DEFAULT_OOS_OUTPUT)
    calibration = read_json(DEFAULT_CAL_OUTPUT)

    required_pass = (
        isinstance(baseline, dict)
        and isinstance(baseline.get("metrics"), dict)
        and isinstance(baseline.get("contracts"), dict)
        and float(baseline["metrics"].get(
            "coverage_actual_seats_in_calibrated_interval_winners", 0.0
        )) >= 0.85
        and baseline["contracts"].get("calibrated_coverage_gate") is True
        and baseline["contracts"].get("historical_conformal_calibration") is True
        and baseline["contracts"].get("calibration_before_target_election") is True
        and baseline["contracts"].get("family_level_calibration") is True
        and baseline["contracts"].get("target_election_excluded_from_calibration") is True
        and baseline["contracts"].get("conformal_nominal_coverage_95") is True
        and baseline.get("source_tier") == "PRIMARY_OFFICIAL"
        and isinstance(oos, dict)
        and oos.get("status") == "PASS"
        and isinstance(calibration, dict)
        and calibration.get("status") == "PASS"
    )

    payload = {
        "schema": "COALICION_COMPLETE_BACKTEST_V1",
        "status": "PASS" if required_pass else "NOT_CERTIFIED",
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "contract": {
            "historical_scope": "2004-2023",
            "oos": "EXPANDING_WINDOW_NO_FUTURE_LEAKAGE",
            "calibration": "STRICT_FAIL_CLOSED",
            "territorial_baseline": "2023_FROM_2019N",
            "territorial_seat_calibration": "PRE_2023_FAMILY_SPECIFIC_CONFORMAL_95",
        },
        "input": {
            "path": str(inp.relative_to(ROOT)),
            "sha256": hashlib.sha256(inp.read_bytes()).hexdigest(),
        },
        "executions": executions,
        "evidence": {
            "baseline_2023": baseline,
            "oos_full": oos,
            "probabilistic_calibration": calibration,
        },
        "closure_rule": (
            "PASS requires baseline execution with territorial coverage >=85%, strict OOS PASS and "
            "probabilistic calibration PASS; otherwise NOT_CERTIFIED."
        ),
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out.read_text(encoding="utf-8"))
    return 0 if required_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
