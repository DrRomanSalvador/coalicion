from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_workflow_resilience import audit_self_healer_contract, audit_telegram_pages_contract, permission_declarations, writer_without_concurrency, audit_product_release_persistence


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
    workflow = workflow.replace('[[ "$count" -lt 5 && "$attempted" -lt 25 ]]', '[[ "$count" -lt 500 && "$attempted" -lt 2500 ]]')
    missing = audit_self_healer_contract(workflow)
    assert "each sweep caps successful reruns and candidate attempts" in missing


def test_audit_rejects_cancelled_run_failed_jobs_only_regression():
    workflow = (ROOT / ".github" / "workflows" / "autonomous_self_healer.yml").read_text(encoding="utf-8")
    workflow = workflow.replace('gh run rerun "$run_id" --repo "$REPOSITORY"', 'gh run rerun "$run_id" --failed --repo "$REPOSITORY"')
    missing = audit_self_healer_contract(workflow)
    assert "cancelled runs use a full rerun" in missing


def test_telegram_pages_workflow_has_permission_aware_first_deployment():
    workflow = (ROOT / ".github" / "workflows" / "telegram_miniapp.yml").read_text(encoding="utf-8")
    assert audit_telegram_pages_contract(workflow) == []


def test_pages_audit_rejects_unavailable_implicit_enablement():
    workflow = (ROOT / ".github" / "workflows" / "telegram_miniapp.yml").read_text(encoding="utf-8")
    workflow = workflow.replace("secrets.PAGES_ADMIN_TOKEN || github.token", "github.token")
    missing = audit_telegram_pages_contract(workflow)
    assert "first-time enablement uses an explicit admin token" in missing


def test_healer_sweep_bounds_candidates_and_continues_after_request_errors():
    workflow = (ROOT / ".github" / "workflows" / "autonomous_self_healer.yml").read_text(encoding="utf-8")
    assert 'sort_by(.created_at)' in workflow
    assert '[[ "$count" -lt 5 && "$attempted" -lt 25 ]]' in workflow
    assert "run_attempt=" in workflow and '"$run_attempt" -lt "$max_attempts"' in workflow
    assert "RERUN_REQUEST_FAILED" in workflow
    assert "continuing sweep" in workflow


def test_permissions_inventory_recognizes_inline_workflow_permissions():
    assert permission_declarations("permissions: {contents: write}\njobs:\n  job:\n    runs-on: ubuntu-latest\n") == (True, False)


def test_permissions_inventory_recognizes_job_level_permissions():
    assert permission_declarations("jobs:\n  job:\n    permissions:\n      contents: read\n") == (False, True)


def test_workflow_audit_blocks_unserialized_remote_writers():
    unsafe = "jobs:\n  job:\n    steps:\n      - run: |\n          git push origin HEAD:main\n"
    safe = "concurrency:\n  group: writer-main\n  cancel-in-progress: false\njobs:\n  job:\n    steps:\n      - run: |\n          git push origin HEAD:main\n"
    assert writer_without_concurrency(unsafe)
    assert not writer_without_concurrency(safe)


def test_product_release_writer_revalidates_main_before_publishing():
    workflow = (ROOT / ".github" / "workflows" / "product_release.yml").read_text(encoding="utf-8")
    assert audit_product_release_persistence(workflow) == []


def test_product_release_audit_rejects_stale_evidence_push():
    workflow = (ROOT / ".github" / "workflows" / "product_release.yml").read_text(encoding="utf-8")
    workflow = workflow.replace('[[ "$remote_sha" != "$GITHUB_SHA" ]]', 'false')
    missing = audit_product_release_persistence(workflow)
    assert "release writer compares main to the tested SHA" in missing
