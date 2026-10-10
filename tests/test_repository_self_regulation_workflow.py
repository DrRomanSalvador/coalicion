from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "repository-self-regulation.yml"
AUTONOMOUS_GATE = ROOT / "scripts" / "autonomous_fix_and_validate.py"


def test_self_regulation_accepts_main_advancing_to_a_descendant_commit():
    source = WORKFLOW.read_text(encoding="utf-8")

    assert 'git merge-base --is-ancestor "$EXPECTED_SHA" "$current_main"' in source
    assert "newer main commit must pass its own push-triggered validation" in source
    assert "Stale validation:" not in source


def test_self_regulation_does_not_run_the_complete_pytest_suite_twice():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    autonomous_gate = AUTONOMOUS_GATE.read_text(encoding="utf-8")

    assert "python -m pytest -q" not in workflow
    assert '["-m", "pytest", "-q"]' in autonomous_gate


def test_expensive_periodic_self_regulation_is_not_started_every_15_minutes():
    source = WORKFLOW.read_text(encoding="utf-8")

    assert 'cron: "17 */6 * * *"' in source
    assert 'cron: "*/15 * * * *"' not in source
