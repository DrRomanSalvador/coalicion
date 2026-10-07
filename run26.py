#!/usr/bin/env python3
"""Single reproducible product pipeline for the 2026 execution.

The runner is prediction-first. Certification/audit code remains available but
is not called by the normal product path.
"""
from __future__ import annotations
import json, subprocess, sys, time
from pathlib import Path

STAGES = [
    ("matrix_2023", ["scripts/acquire_2023_matrix.py"]),
    ("calculator_2023_integration", ["scripts/integrate_2023_calculator.py"]),
    ("calculator_2023_tests", ["-m", "pytest", "tests/test_2023_calculator_integration.py", "tests/test_coalition_reports.py", "-q"]),
    ("coalition_reports_2023", ["scripts/agent2_coalition_reports.py"]),
    ("historical_polls", ["scripts/acquire_historical_polls.py"]),
    ("poll_methodology_tests", ["-m", "pytest", "tests/test_poll_aggregator.py", "tests/test_poll_uncertainty.py", "-q"]),
    ("poll_aggregator_oos", ["scripts/backtest_poll_aggregator.py"]),
    ("historical_secondary", ["scripts/stage_historico_secondary.py"]),
    ("historical_validation", ["scripts/validate_historical_secondary.py"]),
    ("backtest_baseline", ["scripts/backtest_2023_baseline.py"]),
]

def run(name, cmd):
    t=time.time()
    p=subprocess.run([sys.executable,*cmd], text=True, capture_output=True)
    return {
        "stage":name,"command":cmd,"returncode":p.returncode,
        "elapsed_seconds":round(time.time()-t,3),
        "stdout_tail":p.stdout[-4000:],"stderr_tail":p.stderr[-4000:]
    }

def main():
    results=[]
    for name,cmd in STAGES:
        # Existing staged historical scripts use .audit_historico as their
        # working directory. They are execution components, not certification.
        r=run(name,cmd); results.append(r)
        # Continue independent stages; record every blocker in one run.

    survey=Path("data/encuestas_historicas_2004_2023.csv")
    seec_status={
        "status":"READY" if survey.exists() and survey.stat().st_size>173 else "BLOCKED",
        "reason":None,
    }
    if seec_status["status"]=="BLOCKED":
        seec_status["reason"]="No survey archive with usable observations; SEEC production must not invent observations."
    else:
        # Production inference is intentionally delegated to the existing
        # SEEC implementation once its complete likelihood inputs exist.
        seec_status["reason"]="Survey archive exists, but technical fichas/microdata must be materialized before production inference."

    subprocess.run([sys.executable,"scripts/build_sha256_manifest.py"],check=False)
    required = {"matrix_2023", "calculator_2023_integration", "calculator_2023_tests", "coalition_reports_2023"}
    required_failures = [r for r in results if r["stage"] in required and r["returncode"] != 0]
    payload={
        "schema":"RUN26_EXECUTION_V1",
        "prediction_first":True,
        "audit_mode":"INACTIVE",
        "certification_mode":"INACTIVE",
        "stages":results,
        "seec":seec_status,
        "generated_by":"run26.py",
    }
    out=Path("artifacts/run26_state.json")
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,ensure_ascii=False,indent=2))
    if required_failures:
        raise SystemExit(1)
    # The diagnostic bundle is the product of run26; consumers remain fail-closed
    # when required inputs are unavailable.

if __name__=="__main__": main()
