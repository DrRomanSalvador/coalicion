"""Regression contracts for GitHub Actions recovery and checkpoint resilience."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


def test_self_healer_paginates_runs_for_current_main_sha():
    source = (WORKFLOWS / "autonomous_self_healer.yml").read_text(encoding="utf-8")
    assert 'gh api --paginate --slurp "repos/$REPOSITORY/actions/runs?head_sha=$main_sha&per_page=100"' in source
    assert 'select(.head_branch == "main" and .head_sha == $sha)' in source
    assert "select(.run_attempt == 1)" in source
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
