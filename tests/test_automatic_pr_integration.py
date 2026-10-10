import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from automatic_pr_integration import fetch_changed_files, required_checks_for_files, validate_pr_body, fetch_pr_body


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


def test_current_retry_supersedes_old_failure_before_current_run_is_excluded():
    from scripts.automatic_pr_integration import fetch_runs

    payload = json.dumps([{
        "workflow_runs": [
            {"id": 100, "name": "Automatic pull request integration", "head_sha": "abc",
             "status": "completed", "conclusion": "failure", "run_number": 4,
             "run_attempt": 1, "created_at": "2026-10-10T10:00:00Z"},
            {"id": 101, "name": "Automatic pull request integration", "head_sha": "abc",
             "status": "in_progress", "conclusion": None, "run_number": 5,
             "run_attempt": 1, "created_at": "2026-10-10T10:05:00Z"},
            {"id": 102, "name": "Product pipeline 2026", "head_sha": "abc",
             "status": "completed", "conclusion": "success", "run_number": 8,
             "run_attempt": 1, "created_at": "2026-10-10T10:02:00Z"},
        ]
    }])

    def fake_runner(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], 0, stdout=payload, stderr="")

    runs = fetch_runs("owner/repo", "abc", "101", runner=fake_runner)
    assert runs == [{
        "id": 102,
        "name": "Product pipeline 2026",
        "status": "completed",
        "conclusion": "success",
    }]


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

def _valid_pr_body(principle_overrides=None, markdown=True):
    overrides = principle_overrides or {}
    lines = []
    for number in range(1, 26):
        if number in overrides:
            lines.append(f"- **{number:02d}** {overrides[number]}")
        else:
            lines.append(
                f"- **{number:02d}** APLICA — Este principio se evalúa porque el cambio altera "
                f"el contrato de integración número {number:02d}."
            )
    heading = "## " if markdown else ""
    return (
        f"{heading}Causa raíz:\nCausa reproducible y comprobada.\n"
        f"{heading}Solución mínima:\nCambio acotado con regresión.\n"
        f"{heading}Principios afectados (01–25):\n" + "\n".join(lines) + "\n"
        f"{heading}Pruebas ejecutadas y resultado:\nPruebas de contrato preparadas; CI pendiente.\n"
        f"{heading}CI del SHA exacto:\nPendiente de CI para el SHA de esta PR.\n"
        f"{heading}Riesgo y rollback:\nRiesgo delimitado; revertir el commit revierte el cambio.\n"
        f"{heading}Excepciones\nNinguna excepción sin declarar.\n"
    )


def test_pr_body_requires_reasoned_disposition_for_all_25_principles():
    assert validate_pr_body(_valid_pr_body()) == []


def test_pr_body_gate_rejects_missing_principles_even_when_some_are_listed():
    body = _valid_pr_body().replace(
        "- **25** APLICA — Este principio se evalúa porque el cambio altera el contrato de integración número 25.\n",
        "",
    )
    missing = validate_pr_body(body)
    assert any("principle 25 must have exactly one" in item for item in missing)


def test_pr_body_gate_rejects_duplicate_principle_dispositions():
    body = _valid_pr_body() + "\n- **01** APLICA — Duplicado deliberado para probar el bloqueo."
    missing = validate_pr_body(body)
    assert any("principle 01 is declared more than once" in item for item in missing)


def test_pr_body_gate_requires_reasoned_na_disposition():
    body = _valid_pr_body({7: "N/A — no procede"})
    missing = validate_pr_body(body)
    assert any("principle 07 is N/A without an explicit justification" in item for item in missing)


def test_pr_body_gate_accepts_explicitly_justified_na_for_one_principle():
    body = _valid_pr_body({
        7: "N/A — justificación: este cambio no incluye optimizaciones ni modifica rendimiento."
    })
    assert validate_pr_body(body) == []


def test_pr_body_gate_rejects_empty_principle_section():
    body = _valid_pr_body().replace(
        "Principios afectados (01–25):\n" + "\n".join(
            f"- **{number:02d}** APLICA — Este principio se evalúa porque el cambio altera "
            f"el contrato de integración número {number:02d}."
            for number in range(1, 26)
        ) + "\n",
        "Principios afectados (01–25):\n",
    )
    missing = validate_pr_body(body)
    assert any("principle 01 must have exactly one" in item for item in missing)


def test_pr_body_fetch_fails_closed_on_github_api_error():
    def fake_runner(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], 1, stdout="", stderr="HTTP 403")
    try:
        fetch_pr_body("owner/repo", "17", runner=fake_runner)
    except Exception as exc:
        assert "Could not inspect PR description" in str(exc)
    else:
        raise AssertionError("API failure must not bypass mandatory PR evidence")


def test_privileged_merge_gate_executes_trusted_base_code_not_untrusted_pr_code():
    workflow = (ROOT / ".github/workflows/automatic-pr-integration.yml").read_text(encoding="utf-8")
    assert "Checkout trusted base revision for gate script" in workflow
    assert "ref: ${{ github.event.pull_request.base.sha }}" in workflow
    assert "ref: ${{ github.event.pull_request.head.sha }}" not in workflow
    assert "persist-credentials: false" in workflow


def test_pr_gate_enables_auto_squash_merge_without_manual_clicks():
    workflow = (ROOT / ".github/workflows/automatic-pr-integration.yml").read_text(encoding="utf-8")
    assert "name: Automatic PR integration gate" in workflow
    assert "contents: write" in workflow
    assert "pull-requests: write" in workflow
    client = (ROOT / "scripts" / "automatic_pr_integration.py").read_text(encoding="utf-8")
    assert '"gh", "pr", "merge", pr_number, "--auto", "--squash", "--match-head-commit", sha' in client
