import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from automatic_pr_integration import fetch_changed_files, required_checks_for_files


def test_contract_and_resilience_checks_are_always_required():
    required = required_checks_for_files(["README.md"])
    assert "Mandatory engineering contract" in required
    assert "Workflow resilience contract tests" in required
    assert "Methodology validation" in required


def test_code_and_test_changes_require_product_and_exhaustive_gates():
    required = required_checks_for_files(["scripts/automatic_pr_integration.py", "tests/test_gate.py"])
    assert "Product pipeline 2026" in required
    assert "Exhaustive fail-closed validation" in required


def test_dora_and_telegram_changes_require_their_specific_gates():
    required = required_checks_for_files([
        ".github/workflows/deploy_telegram_worker.yml",
        "scripts/dora_metrics.py",
    ])
    assert "DORA engineering metrics" in required
    assert "Telegram Worker CI" in required


def test_docs_only_change_does_not_require_untriggered_product_pipeline():
    required = required_checks_for_files(["README.md"])
    assert "Product pipeline 2026" not in required
    assert "Exhaustive fail-closed validation" not in required


def test_changed_file_fetch_flattens_paginated_github_response():
    payload = json.dumps([
        [{"filename": "README.md"}, {"filename": "scripts/a.py"}],
        [{"filename": "tests/test_a.py"}],
    ])
    def fake_runner(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], 0, stdout=payload, stderr="")
    assert fetch_changed_files("owner/repo", "17", runner=fake_runner) == [
        "README.md", "scripts/a.py", "tests/test_a.py"
    ]


def test_changed_file_fetch_fails_closed_on_api_error():
    def fake_runner(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], 1, stdout="", stderr="HTTP 403")
    try:
        fetch_changed_files("owner/repo", "17", runner=fake_runner)
    except Exception as exc:
        assert "Could not inspect changed PR files" in str(exc)
    else:
        raise AssertionError("API failure must not silently skip required checks")

def test_latest_successful_attempt_supersedes_old_failure_for_same_workflow():
    from scripts.automatic_pr_integration import latest_runs_per_workflow
    runs = [
        {"id": 10, "name": "Contract", "status": "completed", "conclusion": "failure",
         "run_number": 8, "run_attempt": 1, "created_at": "2026-10-10T10:00:00Z"},
        {"id": 10, "name": "Contract", "status": "completed", "conclusion": "success",
         "run_number": 8, "run_attempt": 2, "created_at": "2026-10-10T10:05:00Z"},
        {"id": 11, "name": "Product", "status": "completed", "conclusion": "success",
         "run_number": 2, "run_attempt": 1, "created_at": "2026-10-10T10:01:00Z"},
    ]
    latest = latest_runs_per_workflow(runs)
    by_name = {run["name"]: run for run in latest}
    assert by_name["Contract"]["conclusion"] == "success"
    assert len(latest) == 2


def test_latest_pending_attempt_is_not_hidden_by_older_success():
    from scripts.automatic_pr_integration import latest_runs_per_workflow
    runs = [
        {"id": 20, "name": "Contract", "status": "completed", "conclusion": "success",
         "run_number": 9, "run_attempt": 1, "created_at": "2026-10-10T10:00:00Z"},
        {"id": 20, "name": "Contract", "status": "in_progress", "conclusion": None,
         "run_number": 9, "run_attempt": 2, "created_at": "2026-10-10T10:05:00Z"},
    ]
    latest = latest_runs_per_workflow(runs)
    assert latest == [{"id": 20, "name": "Contract", "status": "in_progress", "conclusion": None}]
