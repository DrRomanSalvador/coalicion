import json
from scripts import notify_webhook

# Regression: Telegram credentials must fail closed.\n\ndef test_missing_telegram_secrets_fails_closed(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    try:
        notify_webhook.send("test")
    except RuntimeError as exc:
        assert "TELEGRAM_BOT_TOKEN" in str(exc)
    else:
        raise AssertionError("notifier must fail closed")

def test_format_report_is_neutral():
    report={"status":"ALERT","checked_at":"2026-10-07T08:00:00+02:00","alert_count":1,
            "alerts":[{"severity":"ALERT","status":"NEW_POLL","source_id":"fixture",
                       "poll":{"pollster":"Demo","publication_date":"2026-10-07"}}],
            "report_path":"artifacts/neutral_poll_report.json"}
    msg=notify_webhook.format_report(report)
    assert "NEW_POLL" in msg
    assert "best" not in msg.lower()
    assert "recommend" not in msg.lower()
