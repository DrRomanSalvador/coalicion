#!/usr/bin/env python3
"""REINA-SEEC: fail-closed orchestrator for the real repository pipeline."""
from __future__ import annotations
import json, os, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "artifacts" / "queue"
REPORTS = ROOT / "reports"
QUEUE.mkdir(parents=True, exist_ok=True)
REPORTS.mkdir(parents=True, exist_ok=True)
MAX_RETRIES = int(os.environ.get("COLMENA_MAX_RETRIES", "3"))
RETRY_DELAY = int(os.environ.get("COLMENA_RETRY_DELAY", "10"))

def now():
    return datetime.now(timezone.utc).isoformat()

def save_result(task_id, result):
    (QUEUE / f"{task_id}.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

def run_task(task_id, argv, retries=MAX_RETRIES):
    started = now()
    last = {}
    for attempt in range(1, retries + 1):
        print(f"\n=== OBRERA: {task_id} | intento {attempt}/{retries} ===")
        try:
            p = subprocess.run(argv, cwd=ROOT, text=True, capture_output=True, timeout=900)
            last = {"stdout": p.stdout[-10000:], "stderr": p.stderr[-10000:], "returncode": p.returncode}
            if p.returncode == 0:
                save_result(task_id, {
                    "task_id": task_id, "status": "PASS", "started_at": started,
                    "finished_at": now(), "attempt": attempt, "argv": argv, **last
                })
                return True
        except subprocess.TimeoutExpired as exc:
            last = {"stdout": str(exc.stdout or "")[-10000:], "stderr": str(exc.stderr or "")[-10000:],
                    "returncode": 124, "error": "TIMEOUT"}
        except Exception as exc:
            last = {"stdout": "", "stderr": repr(exc), "returncode": 1, "error": type(exc).__name__}
        if attempt < retries:
            time.sleep(RETRY_DELAY * attempt)
    save_result(task_id, {
        "task_id": task_id, "status": "FAIL_CLOSED", "started_at": started,
        "finished_at": now(), "attempts": retries, "argv": argv, **last
    })
    return False

def write_report(task_id, title, payload):
    (REPORTS / f"{task_id}.md").write_text(
        f"# {title}\n\nGenerado por REINA-SEEC: {now()}\n\n~~~text\n{payload}\n~~~\n",
        encoding="utf-8"
    )

def main():
    print("=== REINA-SEEC / COLMENA ACTIVATION ===")
    acquired = run_task("acquisition", [sys.executable, "scripts/ai_electoral_data_engine.py", "--retry-on-fail"])
    if not acquired:
        run_task("exhaustive_sources", [
            sys.executable, "scripts/exhaustive_data_acquisition.py", "--search", "--resolve"
        ])
        return 1

    if not run_task("verify_canonical_2023", [sys.executable, "scripts/verify_canonical_2023.py"]):
        return 1

    for task_id, parties in [
        ("coalition_PSOE_SUMAR_2023", ["PSOE", "SUMAR"]),
        ("coalition_PP_Vox_2023", ["PP", "Vox"]),
    ]:
        argv = [sys.executable, "cli.py", "coalition", "--parties", *parties, "--election", "2023"]
        if run_task(task_id, argv):
            p = subprocess.run(argv, cwd=ROOT, text=True, capture_output=True, timeout=900)
            write_report(task_id, f"Coalición {' + '.join(parties)} — 2023", p.stdout)

    argv = [sys.executable, "cli.py", "marginal-seats", "--election", "2023"]
    if run_task("marginal_seats_2023", argv):
        p = subprocess.run(argv, cwd=ROOT, text=True, capture_output=True, timeout=900)
        write_report("marginal_seats_2023", "Escaños marginales — 2023", p.stdout)

    for task_id, party, shift in [
        ("scenario_PSOE_plus2_2023", "PSOE", "+2"),
        ("scenario_PP_plus1_2023", "PP", "+1"),
    ]:
        argv = [
            sys.executable, "cli.py", "scenario", "--party", party, "--shift", shift,
            "--distribution", "uniform_by_province", "--election", "2023"
        ]
        if run_task(task_id, argv):
            p = subprocess.run(argv, cwd=ROOT, text=True, capture_output=True, timeout=900)
            write_report(task_id, f"Escenario {party} {shift} — 2023", p.stdout)

    run_task("product_status", [sys.executable, "scripts/product_status.py"])
    status = {
        "timestamp": now(),
        "primary_matrix": (ROOT / "artifacts/data/election_2023_canonical.json").is_file(),
        "certificate": (ROOT / "artifacts/audit/certificate_2023.json").is_file(),
        "reports": sorted(str(p.relative_to(ROOT)) for p in REPORTS.glob("*.md")),
    }
    (ROOT / "artifacts" / "queen_bee_report.json").write_text(
        json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0 if status["primary_matrix"] and status["certificate"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
