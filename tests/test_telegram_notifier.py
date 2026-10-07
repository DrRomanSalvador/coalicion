from scripts import notify_webhook

# Regression: Telegram credentials must fail closed.
def test_missing_telegram_secrets_fails_closed(monkeypatch):
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


def test_format_electoral_radar_contains_operational_facts():
    report = {
        "status": "OK",
        "as_of": "2026-10-08",
        "election_date": "2026-11-29",
        "alert_count": 2,
        "alerts": [
            {"severity": "ALERT", "title": "Cambio nacional observado: A",
             "facts": {"party": "A", "vote_share_change": 0.01, "seat_change": 2}},
            {"severity": "CRITICAL", "title": "Cierre de comunicación de coaliciones",
             "facts": {"date": "2026-10-16", "days_remaining": 8}},
        ],
        "evidence_refs": ["BOE-A-2026-20742"],
    }
    from scripts.notify_webhook import format_electoral_radar
    msg = format_electoral_radar(report)
    assert "Cambio nacional observado: A" in msg
    assert "+2" in msg
    assert "+1.00 pp" in msg
    assert "Días restantes: 8" in msg
    assert "BOE-A-2026-20742" in msg
    assert "recommend" not in msg.lower()
