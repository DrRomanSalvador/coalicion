import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from automatic_pr_integration import fetch_changed_files, required_checks_for_files, validate_pr_body, fetch_pr_body, fetch_current_pr_head_sha, canonical_principle_titles


def test_contract_and_resilience_checks_are_always_required():
    required = required_checks_for_files(["README.md"])
    assert "Mandatory engineering contract" in required
    assert "Workflow resilience contract tests" in required
    assert "Methodology validation" in required
    assert "Repository-wide self-regulation" in required


def test_code_and_test_changes_require_product_and_exhaustive_gates():
    required = required_checks_for_files(["scripts/automatic_pr_integration.py", "tests/test_gate.py"])
    assert "Product pipeline 2026" in required
    assert "Exhaustive fail-closed validation" in required
    assert "Product pipeline 2026" in required_checks_for_files(["requirements.lock"])
    assert "Product pipeline 2026" in required_checks_for_files(["pyproject.toml"])


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


def test_current_pr_head_sha_is_read_from_live_github_state():
    def fake_runner(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], 0, stdout="a" * 40 + "\n", stderr="")
    assert fetch_current_pr_head_sha("owner/repo", "17", runner=fake_runner) == "a" * 40


def test_current_pr_head_sha_classifies_authorization_failure_for_fast_exit():
    def fake_runner(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], 1, stdout="", stderr="HTTP 403 Resource not accessible by integration")
    try:
        fetch_current_pr_head_sha("owner/repo", "17", runner=fake_runner)
    except Exception as exc:
        assert "authentication/authorization failed" in str(exc)
    else:
        raise AssertionError("Authorization failure must not be retried for 110 minutes")


def test_github_cli_timeout_is_bounded_and_reported_as_transient():
    def fake_runner(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], timeout=30)
    try:
        fetch_current_pr_head_sha("owner/repo", "17", runner=fake_runner)
    except Exception as exc:
        assert "timed out after 30 seconds" in str(exc)
    else:
        raise AssertionError("A stalled GitHub API call must be bounded")


def test_current_pr_head_sha_fails_closed_on_malformed_response():
    def fake_runner(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], 0, stdout="unknown", stderr="")
    try:
        fetch_current_pr_head_sha("owner/repo", "17", runner=fake_runner)
    except Exception as exc:
        assert "malformed current PR head SHA" in str(exc)
    else:
        raise AssertionError("Malformed live SHA must never permit a merge")


def test_path_filtered_pr_workflows_are_mandatory_for_their_triggering_files():
    cases = [
        ("scripts/colmena_queen_hf.py", "Colmena HF — tests aislados"),
        ("scripts/demo_multiparty.py", "Demo multiparty 2023"),
        ("scripts/ingest_official_electoral_history.R", "Inspect official Interior download transport"),
        ("src/web/routes.py", "mvp-validation"),
        ("scripts/run_seec_production.py", "SEEC production real"),
        ("src/telegram_bot.py", "Telegram bot validation"),
        ("scripts/complete_historical_calibration.py", "Unlock verification"),
    ]
    for path, expected_check in cases:
        assert expected_check in required_checks_for_files([path]), path


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

PRINCIPLE_TITLES = canonical_principle_titles()


def _valid_pr_body(principle_overrides=None, markdown=True):
    overrides = principle_overrides or {}
    lines = []
    for number in range(1, 26):
        disposition, rationale = overrides.get(
            number,
            (
                "APLICA",
                f"Este principio se evalúa porque el cambio altera el contrato de integración número {number:02d}.",
            ),
        )
        lines.append(
            f"- **{number:02d}** {disposition} — {PRINCIPLE_TITLES[number]} — {rationale}"
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


def test_canonical_principle_titles_are_loaded_from_the_single_charter_source():
    titles = canonical_principle_titles()
    assert set(titles) == set(range(1, 26))
    charter = (ROOT / "docs" / "ENGINEERING_CHARTER.md").read_text(encoding="utf-8")
    for title in titles.values():
        assert f"**{title}." in charter


def test_pr_body_gate_rejects_present_but_empty_required_evidence_sections():
    body = _valid_pr_body()
    for heading, original in (
        ("Causa raíz:", "Causa reproducible y comprobada."),
        ("Solución mínima:", "Cambio acotado con regresión."),
        ("Pruebas ejecutadas y resultado:", "Pruebas de contrato preparadas; CI pendiente."),
        ("CI del SHA exacto:", "Pendiente de CI para el SHA de esta PR."),
        ("Riesgo y rollback:", "Riesgo delimitado; revertir el commit revierte el cambio."),
        ("Excepciones", "Ninguna excepción sin declarar."),
    ):
        broken = body.replace(f"## {heading}\n{original}", f"## {heading}\n", 1)
        findings = validate_pr_body(broken)
        assert any("has no substantive evidence" in item for item in findings), heading


def test_pr_body_gate_rejects_empty_plain_text_sections_without_markdown():
    body = _valid_pr_body(markdown=False).replace(
        "Causa raíz:\\nCausa reproducible y comprobada.",
        "Causa raíz:\\n",
        1,
    )
    findings = validate_pr_body(body)
    assert any("section 'Causa raíz:' is present but has no substantive evidence" in item for item in findings)


def test_pr_body_gate_rejects_whitespace_only_required_evidence():
    body = _valid_pr_body().replace(
        "## Causa raíz:\nCausa reproducible y comprobada.",
        "## Causa raíz:\n   ",
        1,
    )
    findings = validate_pr_body(body)
    assert any("section 'Causa raíz:' is present but has no substantive evidence" in item for item in findings)


def test_pr_body_requires_reasoned_disposition_for_all_25_principles():
    assert validate_pr_body(_valid_pr_body()) == []


def test_pr_body_gate_rejects_generic_rationale_without_canonical_title():
    body = _valid_pr_body().replace(
        "- **01** APLICA — Legibilidad antes que ingenio — Este principio se evalúa porque el cambio altera el contrato de integración número 01.",
        "- **01** APLICA — Un principio cualquiera — Esta explicación genérica es suficientemente larga pero no identifica el principio canónico.",
    )
    missing = validate_pr_body(body)
    assert any("principle 01 must name its canonical title" in item for item in missing)


def test_pr_body_gate_rejects_canonical_title_without_substantive_rationale():
    body = _valid_pr_body().replace(
        "- **01** APLICA — Legibilidad antes que ingenio — Este principio se evalúa porque el cambio altera el contrato de integración número 01.",
        "- **01** APLICA — Legibilidad antes que ingenio",
    )
    missing = validate_pr_body(body)
    assert any("principle 01 needs a concrete rationale after its canonical title" in item for item in missing)


def test_pr_body_gate_rejects_missing_principles_even_when_some_are_listed():
    body = _valid_pr_body().replace(
        "- **25** APLICA — Utilidad y responsabilidad — Este principio se evalúa porque el cambio altera el contrato de integración número 25.\n",
        "",
    )
    missing = validate_pr_body(body)
    assert any("principle 25 must have exactly one" in item for item in missing)


def test_pr_body_gate_rejects_duplicate_principle_dispositions():
    body = _valid_pr_body().replace(
        "- **02** APLICA — Automatizar lo repetible — Este principio se evalúa porque el cambio altera el contrato de integración número 02.\n",
        "- **02** APLICA — Automatizar lo repetible — Este principio se evalúa porque el cambio altera el contrato de integración número 02.\n"
        "- **01** APLICA — Legibilidad antes que ingenio — Duplicado deliberado dentro de la sección.",
    )
    missing = validate_pr_body(body)
    assert any("principle 01 is declared more than once" in item for item in missing)


def test_pr_body_gate_requires_reasoned_na_disposition():
    body = _valid_pr_body({
        7: ("N/A", "no procede en el alcance concreto de este cambio")
    })
    missing = validate_pr_body(body)
    assert any("principle 07 is N/A without an explicit justification" in item for item in missing)


def test_pr_body_gate_accepts_explicitly_justified_na_for_one_principle():
    body = _valid_pr_body({
        7: ("N/A", "justificación: este cambio no incluye optimizaciones ni modifica rendimiento.")
    })
    assert validate_pr_body(body) == []


def test_pr_body_gate_rejects_empty_principle_section():
    body = _valid_pr_body().replace(
        "Principios afectados (01–25):\n" + "\n".join(
            f"- **{number:02d}** APLICA — {PRINCIPLE_TITLES[number]} — "
            f"Este principio se evalúa porque el cambio altera el contrato de integración número {number:02d}."
            for number in range(1, 26)
        ) + "\n",
        "Principios afectados (01–25):\n",
    )
    missing = validate_pr_body(body)
    assert any("principle 01 must have exactly one" in item for item in missing)



def test_empty_pr_body_is_returned_for_fail_closed_evidence_validation():
    def fake_runner(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], 0, stdout="", stderr="")
    body = fetch_pr_body("owner/repo", "17", runner=fake_runner)
    assert body == ""
    assert validate_pr_body(body)


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
    assert "name: Verify mandatory agent contract" not in workflow
    assert "github.event.pull_request.head.repo.full_name == github.repository" in workflow
    assert "pull_request_target:" in workflow
    assert "  pull_request:\n" not in workflow
    assert "edited" in workflow
    assert "Suspend queued auto-merge before revalidating PR changes" in workflow
    assert "github.event.action == 'edited' || github.event.action == 'synchronize'" in workflow
    assert "gh pr merge \"$PR_NUMBER\" --repo \"$GH_REPO\" --disable-auto" in workflow
    assert "contents: write" in workflow
    assert "pull-requests: write" in workflow
    client = (ROOT / "scripts" / "automatic_pr_integration.py").read_text(encoding="utf-8")
    assert '"gh", "pr", "merge", pr_number, "--auto", "--squash", "--match-head-commit", sha' in client
