#!/usr/bin/env python3
"""Fail-closed repository discovery, validation and execution gate.

The script never invents commands. It inventories the checkout first, runs only
tests/scripts that actually exist, records missing prerequisites explicitly,
and exits non-zero unless every requested executable gate passes.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts" / "verification" / "autonomous_validation.json"


@dataclass
class Result:
    name: str
    status: str
    command: list[str] | None = None
    returncode: int | None = None
    detail: str = ""


def run(name: str, command: list[str], timeout: int = 900) -> Result:
    p = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )
    detail = p.stdout[-12000:]
    return Result(
        name=name,
        status="PASS" if p.returncode == 0 else "FAIL",
        command=command,
        returncode=p.returncode,
        detail=detail,
    )


def inventory() -> dict[str, list[str]]:
    return {
        "scripts": sorted(str(p.relative_to(ROOT)) for p in (ROOT / "scripts").glob("*.py")),
        "tests": sorted(str(p.relative_to(ROOT)) for p in (ROOT / "tests").glob("test_*.py")),
        "src": sorted(str(p.relative_to(ROOT)) for p in (ROOT / "src").glob("*.py")),
    }


def imports_pymc(paths: list[str]) -> bool:
    for rel in paths:
        try:
            tree = ast.parse((ROOT / rel).read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [n.name for n in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            if any(n == "pymc" or n.startswith("pymc.") or n == "pytensor" or n.startswith("pytensor.") for n in names):
                return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    inv = inventory()
    results: list[Result] = []

    # Phase 0: syntax and dependency discovery.
    results.append(run("python_compile", [sys.executable, "-m", "compileall", "-q", "src", "scripts", "tests"]))
    pymc_required = imports_pymc(inv["src"] + inv["tests"])
    try:
        import pymc  # noqa: F401
        pymc_available = True
        pymc_detail = "PyMC importable"
    except ImportError as exc:
        pymc_available = False
        pymc_detail = str(exc)
    results.append(
        Result(
            "pymc_runtime",
            "PASS" if (not pymc_required or pymc_available) else "PENDING",
            detail=pymc_detail,
        )
    )

    # Phase 1: targeted SEEC tests only if the test file exists.
    seec_test = ROOT / "tests" / "test_seec_bayesian.py"
    if seec_test.exists():
        results.append(run("seec_targeted", [sys.executable, "-m", "pytest", "-q", str(seec_test)]))
    else:
        results.append(Result("seec_targeted", "MISSING", detail="tests/test_seec_bayesian.py"))

    # Phase 2: complete available test suite.
    if inv["tests"]:
        results.append(run("pytest_full", [sys.executable, "-m", "pytest", "-q"], timeout=1800))
    else:
        results.append(Result("pytest_full", "MISSING", detail="tests/*.py"))

    # Phase 3: run only existing backtest scripts. Do not fabricate a data path.
    backtests = [p for p in inv["scripts"] if Path(p).name.startswith("backtest_") and p.endswith(".py")]
    for rel in backtests:
        if rel.endswith("backtest_2023_baseline.py"):
            staged = ROOT / ".audit_historico" / "historical_province_secondary.csv"
            if not staged.exists():
                stage = ROOT / "scripts" / "stage_historico_secondary.py"
                validate = ROOT / "scripts" / "validate_historical_secondary.py"
                if stage.exists() and validate.exists():
                    results.append(run("backtest_prerequisite:secondary_staging", [sys.executable, str(stage)], timeout=1800))
                    results.append(run("backtest_prerequisite:secondary_validation", [sys.executable, str(validate)], timeout=900))
                else:
                    results.append(Result(
                        "backtest_prerequisite",
                        "MISSING",
                        detail="No existe el staging secundario requerido por el backtest",
                    ))
            if not staged.exists():
                results.append(Result(
                    f"backtest:{rel}",
                    "PENDING",
                    command=[sys.executable, rel],
                    detail="No se puede ejecutar el backtest sin historical_province_secondary.csv",
                ))
                continue
        results.append(run(f"backtest:{rel}", [sys.executable, rel], timeout=1800))

    # Phase 4: existing deterministic verification scripts.
    for rel in ("scripts/verify_seec_v4.py", "scripts/master_certification.py"):
        if (ROOT / rel).exists():
            results.append(run(f"verification:{rel}", [sys.executable, rel], timeout=900))

    # Missing capabilities are explicit; no invented replacement is executed.
    missing = []
    expected_capabilities = {
        "full_oos_pipeline": not any("oos" in p.lower() and p.endswith(".py") for p in inv["scripts"]),
        "probabilistic_calibration_pipeline": not any("calibr" in p.lower() and p.endswith(".py") for p in inv["scripts"]),
        "temporal_decay_script": not (ROOT / "scripts" / "add_temporal_decay.py").exists(),
        "prediction_oos_integration_script": not (ROOT / "scripts" / "integrate_oos_in_prediction.py").exists(),
        "full_backtest_script": not (ROOT / "scripts" / "run_full_backtest.py").exists(),
    }
    for capability, absent in expected_capabilities.items():
        if absent:
            missing.append(capability)

    payload = {
        "status": "ALL_SUCCESS"
        if all(r.status == "PASS" for r in results)
        and not missing
        and (not pymc_required or pymc_available)
        else "BLOCKED",
        "branch": os.environ.get("GITHUB_REF_NAME", "local"),
        "inventory": inv,
        "pymc_required": pymc_required,
        "pymc_available": pymc_available,
        "missing_capabilities": missing,
        "results": [asdict(r) for r in results],
    }
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["status"] == "ALL_SUCCESS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
