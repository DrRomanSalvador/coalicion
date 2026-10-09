from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_workflow_resilience import audit_self_healer_contract


def test_main_self_healer_has_all_blocking_recovery_contracts():
    workflow = (ROOT / ".github" / "workflows" / "autonomous_self_healer.yml").read_text(encoding="utf-8")
    assert audit_self_healer_contract(workflow) == []


def test_audit_rejects_unpaginated_repository_wide_run_scan():
    workflow = (ROOT / ".github" / "workflows" / "autonomous_self_healer.yml").read_text(encoding="utf-8")
    workflow = workflow.replace(
        'gh api --paginate --slurp "repos/$REPOSITORY/actions/runs?head_sha=$main_sha&per_page=100"',
        'gh api "repos/$REPOSITORY/actions/runs?per_page=100"',
    )
    missing = audit_self_healer_contract(workflow)
    assert "query is paginated and scoped to current main SHA" in missing


def test_audit_rejects_unbounded_retry_sweep():
    workflow = (ROOT / ".github" / "workflows" / "autonomous_self_healer.yml").read_text(encoding="utf-8")
    workflow = workflow.replace('[[ "$count" -lt 5 ]]', '[[ "$count" -lt 500 ]]')
    missing = audit_self_healer_contract(workflow)
    assert "each sweep caps rerun requests" in missing


def test_audit_rejects_cancelled_run_failed_jobs_only_regression():
    workflow = (ROOT / ".github" / "workflows" / "autonomous_self_healer.yml").read_text(encoding="utf-8")
    workflow = workflow.replace('gh run rerun "$run_id" --repo "$REPOSITORY"', 'gh run rerun "$run_id" --failed --repo "$REPOSITORY"')
    missing = audit_self_healer_contract(workflow)
    assert "cancelled runs use a full rerun" in missing
