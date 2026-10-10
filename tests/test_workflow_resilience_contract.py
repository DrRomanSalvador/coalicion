"""Regression contracts for GitHub Actions recovery and checkpoint resilience."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


def test_self_healer_paginates_runs_for_current_main_sha():
    source = (WORKFLOWS / "autonomous_self_healer.yml").read_text(encoding="utf-8")
    assert 'gh api --paginate --slurp "repos/$REPOSITORY/actions/runs?head_sha=$main_sha&per_page=100"' in source
    assert 'select(.head_branch == "main" and .head_sha == $sha)' in source
    assert 'select(.status == "completed" and .run_attempt < 3)' in source
    assert "inputs.failed_run_id || 'scheduled-sweep'" in source
    assert "cancel-in-progress: false" in source
    assert 'actions/runs?per_page=100")' not in source


def test_self_healer_uses_correct_retry_mode_and_rejects_active_runs():
    source = (WORKFLOWS / "autonomous_self_healer.yml").read_text(encoding="utf-8")
    assert 'queued|in_progress|waiting|requested|pending)' in source
    assert 'if [[ "$conclusion" == "cancelled" ]]' in source
    assert 'gh run rerun "$run_id" --repo "$REPOSITORY"' in source
    assert 'gh run rerun "$run_id" --failed --repo "$REPOSITORY"' in source


def test_colmena_checkpoint_stale_sha_is_revalidated_before_persistence():
    source = (WORKFLOWS / "colmena_atomic_swarm.yml").read_text(encoding="utf-8")
    assert 'if [ "$checkpoint_rc" -eq 3 ]; then' in source
    assert "revalidating latest main" in source
    assert 'git fetch origin main' in source
    assert 'git push origin HEAD:main' in source


def test_workflow_files_have_unique_names_and_expected_yaml_extension():
    paths = sorted(WORKFLOWS.glob("*.yml"))
    assert paths, "No GitHub Actions workflow files found"
    assert len({path.name for path in paths}) == len(paths)
    assert all(path.is_file() and path.stat().st_size > 0 for path in paths)



def test_exhaustive_validation_runs_and_publishes_the_workflow_audit():
    source = (WORKFLOWS / "exhaustive_validation.yml").read_text(encoding="utf-8")
    assert "python scripts/audit_workflow_resilience.py" in source
    assert "artifacts/verification/workflow_resilience_audit.json" in source


def test_static_audit_labels_heuristics_for_human_review_not_as_certified_defects():
    source = (ROOT / "scripts" / "audit_workflow_resilience.py").read_text(encoding="utf-8")
    assert '"classification": "REVIEW_REQUIRED"' in source
    assert "Static inspection does not execute workflows" in source
    assert "actionlint/CI" in source


def test_oos_evidence_persistence_rechecks_tested_sha_and_retries_races():
    source = (WORKFLOWS / "oos-calibration.yml").read_text(encoding="utf-8")
    assert 'tested_sha="$(git rev-parse HEAD)"' in source
    assert 'git diff --name-only "$tested_sha" "$current_sha"' in source
    assert 'for attempt in 1 2 3 4 5; do' in source
    assert 'git push origin HEAD:main' in source
    assert "stale evidence will not be published" in source


def test_colmena_agent_evidence_persistence_retries_concurrent_branch_updates():
    source = (WORKFLOWS / "colmena_hf_agents.yml").read_text(encoding="utf-8")
    assert 'for attempt in 1 2 3 4 5; do' in source
    assert 'git fetch origin "$branch"' in source
    assert 'git rebase "origin/$branch"' in source
    assert 'git push origin "HEAD:$branch"' in source
    assert "refusing to overwrite newer state" in source


def test_methodology_ci_cancels_superseded_runs_per_ref():
    for name in ("methodology-validation.yml", "methodology_integration.yml", "methodology_validation.yml"):
        source = (WORKFLOWS / name).read_text(encoding="utf-8")
        assert "concurrency:" in source
        assert "github.event.pull_request.number || github.ref" in source
        assert "cancel-in-progress: true" in source


def test_scheduled_electoral_radar_serializes_runs_per_ref():
    source = (WORKFLOWS / "electoral_intelligence.yml").read_text(encoding="utf-8")
    assert "group: electoral-intelligence-${{ github.ref }}" in source
    assert "cancel-in-progress: false" in source


def test_stale_colmena_checkpoint_is_reported_as_skip_not_failure():
    source = (ROOT / "scripts" / "colmena_checkpoint.py").read_text(encoding="utf-8")
    assert "CHECKPOINT_SKIPPED_STALE_VALIDATION" in source
    assert 'fail(f"stale validation:' not in source
    workflow = (WORKFLOWS / "colmena_atomic_swarm.yml").read_text(encoding="utf-8")
    assert 'if [ "$checkpoint_rc" -eq 3 ]; then' in workflow


def test_historical_self_healer_refuses_to_retry_a_stale_main_sha():
    source = (WORKFLOWS / "historical-ci-self-healer.yml").read_text(encoding="utf-8")
    assert "current_sha=" in source and "commits/main" in source and "--jq" in source
    assert "HISTORICAL_STALE_RUN" in source
    assert 'if [ "$run_sha" != "$current_sha" ]; then' in source
    assert 'gh run rerun "$run_id" --repo "$REPOSITORY"' in source


def test_self_healer_reports_exhausted_failures_even_when_retryable_candidates_exist():
    source = (WORKFLOWS / "autonomous_self_healer.yml").read_text(encoding="utf-8")
    assert "EXHAUSTED_RETRY_BUDGET" in source
    assert "Detect exhausted failures on every sweep" in source
    assert 'select(.status == "completed" and .run_attempt >= 3)' in source
    assert 'select(.status == "completed" and .run_attempt < 3)' in source
    assert '[[ "${#candidates[@]}" -eq 0 ]]' in source
    assert source.index("EXHAUSTED_RETRY_BUDGET") < source.index('if [[ "$failures" -gt 0 ]]; then')
    assert 'printf \'%s\\\\n\' "$exhausted"' not in source
    assert source.count('printf \'%s\\n\' "$exhausted" | tee -a "$GITHUB_STEP_SUMMARY"') == 2


def test_global_orchestrator_automatically_checks_for_stuck_canonical_runs():
    source = (WORKFLOWS / "global_repository_orchestrator.yml").read_text(encoding="utf-8")
    assert "workflow_dispatch:" in source
    assert 'cron: "*/15 * * * *"' in source
    assert "Release only genuinely stuck canonical runs" in source
    assert "10800" in source
    assert "actions/runs?per_page=100&branch=main" in source



def test_auto_merge_gate_paginates_and_excludes_only_its_own_run():
    workflow = (WORKFLOWS / "automatic-pr-integration.yml").read_text(encoding="utf-8")
    source = (ROOT / "scripts" / "automatic_pr_integration.py").read_text(encoding="utf-8")
    assert '"gh",\n            "api",\n            "--paginate",\n            "--slurp"' in source
    assert 'CURRENT_RUN_ID: ${{ github.run_id }}' in workflow
    assert 'str(run.get("id", "")) == current_run_id' in source
    assert 'run.get("head_sha") != sha' in source
    assert 'if run.get("name") != self_name' not in source


def test_auto_merge_gate_blocks_failed_missing_and_stale_commit_checks():
    workflow = (WORKFLOWS / "automatic-pr-integration.yml").read_text(encoding="utf-8")
    source = (ROOT / "scripts" / "automatic_pr_integration.py").read_text(encoding="utf-8")
    assert 'run["conclusion"] not in {"success", "skipped"}' in source
    assert 'missing_success = sorted(required - completed_successfully)' in source
    assert "Blocking merge: checks did not reach a stable all-green state within 110 minutes." in source
    assert '"--match-head-commit"' in source
    assert 'sha,' in source


def test_poll_monitor_fails_closed_after_persisting_blocked_state():
    workflow = (WORKFLOWS / "poll_monitor.yml").read_text(encoding="utf-8")
    monitor = (ROOT / "src" / "poll_monitor.py").read_text(encoding="utf-8")
    assert "Fail closed after persisting monitor state" in workflow
    assert "MONITOR_EXIT_CODE" in workflow
    assert "steps.monitor.outputs.monitor_exit_code" in workflow
    assert 'raise SystemExit(1 if result.get("status") == "BLOCKED" else 0)' in monitor
    assert 'payload["notification_status"]' in monitor


def test_continuous_supervisor_retries_by_default_except_explicit_dispatch_opt_out():
    source = (WORKFLOWS / "continuous-workflow-supervisor.yml").read_text(encoding="utf-8")
    assert "RETRY_FAILED: ${{ github.event_name != 'workflow_dispatch' || inputs.retry_failed }}" in source
    assert "RETRY_FAILED: ${{ inputs.retry_failed != false }}" not in source

def test_continuous_supervisor_bounds_api_scan_to_configured_lookback_and_current_main_sha():
    source = (WORKFLOWS / "continuous-workflow-supervisor.yml").read_text(encoding="utf-8")
    assert 'commits/main' in source
    assert 'head_sha=$main_sha&created=%3E%3D${since}' in source
    assert "gh api --paginate" in source
    assert 'if run.get("created_at", "") < since:' in source

def test_2023_matrix_acquisition_installs_pytest_before_invariant_suite():
    source = (WORKFLOWS / "acquire_matrix_2023.yml").read_text(encoding="utf-8")
    install_step = source.split("      - name: Instalar dependencias de adquisición", 1)[1].split("      - name:", 1)[0]
    assert "pytest" in install_step
    assert "python -m pytest -q tests/test_neutral_coalition.py" in source
    assert 'push:\n    branches: [main]\n    paths:\n      - ".github/workflows/acquire_matrix_2023.yml"' in source

def test_auto_merge_gate_uses_testable_fail_closed_api_client():
    workflow = (WORKFLOWS / "automatic-pr-integration.yml").read_text(encoding="utf-8")
    client = (ROOT / "scripts" / "automatic_pr_integration.py").read_text(encoding="utf-8")
    assert "actions: read" in workflow
    assert "GH_TOKEN: ${{ github.token }}" in workflow
    assert "run: python scripts/automatic_pr_integration.py" in workflow
    assert "Checkout exact PR head for gate script" in workflow
    assert "ref: ${{ github.event.pull_request.head.sha }}" in workflow
    assert "persist-credentials: false" in workflow
    assert "GitHubAPIAuthError" in client
    assert "GitHub Actions API authentication/authorization failed" in client
    assert "except GitHubAPIAuthError as exc:" in client
    assert "if not value" in client


def test_auto_merge_gate_authentication_errors_fail_fast_without_waiting():
    from types import SimpleNamespace

    import pytest

    from scripts.automatic_pr_integration import GitHubAPIAuthError, fetch_runs

    def unauthorized_runner(*args, **kwargs):
        assert kwargs["capture_output"] is True
        assert kwargs["check"] is False
        return SimpleNamespace(
            returncode=1,
            stdout="",
            stderr="gh: HTTP 401: Bad credentials",
        )

    with pytest.raises(GitHubAPIAuthError, match="HTTP 401"):
        fetch_runs("DrRomanSalvador/coalicion", "a" * 40, "123", runner=unauthorized_runner)


def test_auto_merge_gate_403_permissions_failure_is_not_retried_as_transient():
    from types import SimpleNamespace

    import pytest

    from scripts.automatic_pr_integration import GitHubAPIAuthError, fetch_runs

    def forbidden_runner(*args, **kwargs):
        return SimpleNamespace(
            returncode=1,
            stdout="",
            stderr="gh: HTTP 403: Resource not accessible by integration",
        )

    with pytest.raises(GitHubAPIAuthError, match="HTTP 403"):
        fetch_runs("DrRomanSalvador/coalicion", "b" * 40, "456", runner=forbidden_runner)


def test_auto_merge_gate_filters_runs_to_exact_sha_and_excludes_only_current_run():
    import json
    from types import SimpleNamespace

    from scripts.automatic_pr_integration import fetch_runs

    payload = [
        {
            "workflow_runs": [
                {"id": 1, "head_sha": "c" * 40, "name": "Required", "status": "completed", "conclusion": "success"},
                {"id": 2, "head_sha": "c" * 40, "name": "Gate itself", "status": "in_progress", "conclusion": None},
                {"id": 3, "head_sha": "d" * 40, "name": "Stale revision", "status": "completed", "conclusion": "failure"},
            ]
        }
    ]

    def successful_runner(args, **kwargs):
        assert args[:4] == ["gh", "api", "--paginate", "--slurp"]
        return SimpleNamespace(returncode=0, stdout=json.dumps(payload), stderr="")

    runs = fetch_runs("DrRomanSalvador/coalicion", "c" * 40, "2", runner=successful_runner)
    assert runs == [
        {"id": 1, "name": "Required", "status": "completed", "conclusion": "success"}
    ]

def test_batch_workflow_uses_gh_cli_token_handling_and_reports_auth_failures_explicitly():
    source = (WORKFLOWS / "batch_workflow_validation.yml").read_text(encoding="utf-8")
    assert "actions: write" in source
    assert "contents: read" in source
    assert "GH_TOKEN: ${{ github.token }}" in source
    assert 'command = ["gh", "api", path, "--method", method]' in source
    assert "urllib.request.urlopen" not in source
    assert "GitHub API authentication failed (401 Bad credentials)" in source
    assert "GitHub API authorization failed (403)" in source
    assert "if not token:" in source
    assert 'if not path.startswith("repos/")' in source

def test_batch_validation_dispatches_one_prioritized_workflow_at_a_time():
    source = (WORKFLOWS / "batch_workflow_validation.yml").read_text(encoding="utf-8")
    assert '"workflow-resilience-tests.yml": 0' in source
    assert '"exhaustive_validation.yml": 1' in source
    assert '"mc-10000.yml": 2' in source
    assert '"source": "queued"' in source
    assert 'Strict single-flight dispatch' in source
    assert 'queued = next((entry for entry in entries if entry["state"] == "queued"), None)' in source
    assert 'if queued is not None and not active:' in source
    assert '"state": "waiting"' in source
