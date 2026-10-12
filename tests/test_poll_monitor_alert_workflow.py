from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "poll_monitor.yml"
MONITOR = ROOT / "src" / "poll_monitor.py"


def test_poll_monitor_accepts_existing_reina_token_secret_for_telegram_alerts():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN || secrets.REINA_TOKEN }}" in workflow
    monitor = MONITOR.read_text(encoding="utf-8")
    assert 'os.environ.get("TELEGRAM_BOT_TOKEN")' in monitor
    assert 'os.environ.get("TELEGRAM_ALLOWED_CHATS", "")' in monitor


def test_poll_alert_workflow_runs_every_five_minutes_and_fails_closed_on_undelivered_alerts():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert 'cron: "*/5 * * * *"' in workflow
    assert "Fail closed after persisting monitor state" in workflow
    assert "undelivered required alerts" in workflow
