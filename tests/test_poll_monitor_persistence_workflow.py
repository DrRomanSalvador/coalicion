from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_poll_monitor_persists_state_without_writing_to_protected_main():
    workflow = (ROOT / ".github" / "workflows" / "poll_monitor.yml").read_text(encoding="utf-8")
    assert "Restore durable poll state from dedicated branch" in workflow
    assert "automation/poll-monitor-state" in workflow
    assert "git push origin HEAD:main" not in workflow
    assert "git push --force-with-lease=" in workflow
    assert "artifacts/poll_monitor_state.json" in workflow
    assert "artifacts/survey_history.jsonl" in workflow
    assert "ci_evidence/poll_source_coverage.json" in workflow


def test_poll_monitor_dispatch_uses_persisted_snapshot_commit():
    workflow = (ROOT / ".github" / "workflows" / "poll_monitor.yml").read_text(encoding="utf-8")
    assert 'client_payload[commit]=${{ steps.persist.outputs.commit || github.sha }}' in workflow
