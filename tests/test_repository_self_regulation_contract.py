"""Contract tests for repository-wide continuous self-regulation."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "repository-self-regulation.yml"


def test_repository_self_regulation_covers_all_main_pushes_prs_and_scheduled_sweeps():
    source = WORKFLOW.read_text(encoding="utf-8")
    assert "push:\n    branches: [main]" in source
    assert "pull_request:" in source
    assert 'cron: "*/15 * * * *"' in source
    assert "workflow_dispatch:" in source
    assert "paths:" not in source


def test_repository_self_regulation_tests_and_rechecks_exact_commit():
    source = WORKFLOW.read_text(encoding="utf-8")
    assert "EXPECTED_SHA:" in source
    assert 'actual="$(git rev-parse HEAD)"' in source
    assert "python -m pytest -q" in source
    assert "python scripts/autonomous_fix_and_validate.py --strict" in source
    assert 'current_main="$(git rev-parse origin/main)"' in source
    assert '[[ "$current_main" != "$EXPECTED_SHA" ]]' in source


def test_repository_self_regulation_captures_diagnostics_and_tracks_unresolved_failures():
    source = WORKFLOW.read_text(encoding="utf-8")
    assert "if: always()" in source
    assert "actions/upload-artifact@v4" in source
    assert "if: failure() && github.event_name != 'pull_request'" in source
    assert "gh issue create" in source
    assert "Do not mark the repository healthy or bypass a failed gate." in source


def test_repository_self_regulation_has_no_fail_open_steps():
    source = WORKFLOW.read_text(encoding="utf-8")
    assert "continue-on-error: true" not in source
    assert "|| true" not in source
