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
