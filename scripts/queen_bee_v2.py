#!/usr/bin/env python3
"""REINA-SEEC v2: deterministic, fail-closed orchestration.

The orchestrator retries execution failures, records every attempt, and never
turns a secondary source, missing artifact, or ambiguous result into a primary
certification. Recovery means retrying or gathering more evidence, not inventing
or defaulting electoral values.
"""
from __future__ import annotations
import json, os, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "artifacts" / "queue"
REPORTS = ROOT / "reports"
QUEUE.mkdir(parents=True, exist_ok=True)
REPORTS.mkdir(parents=True, exist_ok=True)
RETRIES = int(os.environ.get("COLMENA_MAX_RETRIES", "3"))
BASE_DELAY = int(os.environ.get("COLMENA_RETRY_DELAY", "10"))

def now(): return datetime.now(timezone.utc).isoformat()

def record(task, status, attempt, argv, stdout="", stderr="", error=None):
    payload = {
        "task_id": task, "status": status, "attempt": attempt,
        "timestamp": now(), "argv": argv,
        "stdout": stdout[-12000:], "stderr": stderr[-12000:]
    }
    if error: payload["error"] = error
    (QUEUE / f"{task}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")

def run(task, argv, retries=RETRIES, timeout=900):
    for attempt in range(1, retries + 1):
        print(f"=== OBRERA {task}: {attempt}/{retries} ===")
        try:
            p = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
            if p.returncode == 0:
                record(task, "PASS", attempt, argv, p.stdout, p.stderr)
                return True, p.stdout
            record(task, "RETRYABLE_FAILURE" if attempt < retries else "FAIL_CLOSED",
                   attempt, argv, p.stdout, p.stderr)
        except subprocess.TimeoutExpired as exc:
            record(task, "TIMEOUT", attempt, argv, str(exc.stdout or ""), str(exc.stderr or ""), "TIMEOUT")
        except Exception as exc:
            record(task, "EXECUTION_ERROR", attempt, argv, "", "", repr(exc))
        if attempt < retries:
            time.sleep(BASE_DELAY * attempt)
    return False, ""

def capture_report(task, title, argv):
    ok, out = run(task, argv)
    if ok:
        (REPORTS / f"{task}.md").write_text(f"# {title}\n\nGenerado: {now()}\n\n~~~json\n{out}\n~~~\n", encoding="utf-8")
    return ok

def main():
    print("=== ABEJA REINA v2 / REINA-SEEC ===")
    acquisition = run("acquisition", [sys.executable, "scripts/ai_electoral_data_engine.py", "--retry-on-fail"])
    if not acquisition[0]:
        # Fallback = evidence acquisition only. It does NOT publish a secondary
        # matrix as official and does NOT unblock the primary gate.
        run("exhaustive_sources", [sys.executable, "scripts/exhaustive_data_acquisition.py", "--search", "--resolve"])
        return 1

    if not run("verify_canonical_2023", [sys.executable, "scripts/verify_canonical_2023.py"])[0]:
        return 1

    # The repository currently has no separate validate/reconcile/audit scripts;
    # those functions are integrated into the canonical data engine and verifier.
    tasks = [
        ("coalition_PSOE_SUMAR_2023", "Coalición PSOE + SUMAR — 2023",
         [sys.executable, "cli.py", "coalition", "--parties", "PSOE", "SUMAR", "--election", "2023"]),
        ("coalition_PP_Vox_2023", "Coalición PP + Vox — 2023",
         [sys.executable, "cli.py", "coalition", "--parties", "PP", "Vox", "--election", "2023"]),
        ("marginal_seats_2023", "Escaños marginales — 2023",
         [sys.executable, "cli.py", "marginal-seats", "--election", "2023"]),
        ("scenario_PSOE_plus2_2023", "Escenario PSOE +2 puntos — 2023",
         [sys.executable, "cli.py", "scenario", "--party", "PSOE", "--shift", "+2",
          "--distribution", "uniform_by_province", "--election", "2023"]),
        ("scenario_PP_plus1_2023", "Escenario PP +1 punto — 2023",
         [sys.executable, "cli.py", "scenario", "--party", "PP", "--shift", "+1",
          "--distribution", "uniform_by_province", "--election", "2023"]),
    ]
    results = {}
    for task, title, argv in tasks:
        results[task] = capture_report(task, title, argv)

    status_ok = (
        Path("artifacts/data/election_2023_canonical.json").is_file()
        and Path("artifacts/audit/certificate_2023.json").is_file()
        and all(results.values())
    )
    report = {
        "timestamp": now(),
        "status": "COMPLETE" if status_ok else "PARTIAL_FAIL_CLOSED",
        "results": results,
        "primary_matrix": Path("artifacts/data/election_2023_canonical.json").is_file(),
        "certificate": Path("artifacts/audit/certificate_2023.json").is_file(),
    }
    (ROOT / "artifacts" / "queen_bee_v2_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if status_ok else 1

if __name__ == "__main__":
    raise SystemExit(main())
