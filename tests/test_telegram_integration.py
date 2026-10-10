import json
from pathlib import Path

from src.telegram_persistence import SNAPSHOT, STATE_FILES, restore, snapshot
from src.telegram_timezone import today_madrid, now_madrid


def test_timezone_is_explicit_madrid():
    assert now_madrid().tzinfo is not None
    assert now_madrid().utcoffset() is not None
    assert today_madrid().isoformat() == now_madrid().date().isoformat()


def test_persistence_roundtrip(tmp_path, monkeypatch):
    snapshot_path = tmp_path / "telegram_state.json"
    config = tmp_path / "config.json"
    users = tmp_path / "users.json"
    alerts = tmp_path / "alerts.json"
    digest = tmp_path / "digest.json"
    monkeypatch.setattr("src.telegram_persistence.SNAPSHOT", snapshot_path)
    monkeypatch.setattr("src.telegram_persistence.STATE_FILES", {
        "config": config, "user_state": users, "alert_state": alerts, "digest_state": digest,
    })
    config.write_text(json.dumps({"chats": {"123": {"frequency": "daily"}}}), encoding="utf-8")
    users.write_text(json.dumps({"users": {"42": {"current": "/briefing"}}}), encoding="utf-8")
    alerts.write_text(json.dumps({"123": ["x"]}), encoding="utf-8")
    digest.write_text(json.dumps({"daily": "2026-10-08"}), encoding="utf-8")
    snapshot()
    config.unlink(); users.unlink(); alerts.unlink(); digest.unlink()
    restore()
    assert json.loads(config.read_text(encoding="utf-8"))["chats"]["123"]["frequency"] == "daily"
    assert json.loads(users.read_text(encoding="utf-8"))["users"]["42"]["current"] == "/briefing"

from src import telegram_bot


def test_authorization_is_fail_closed(monkeypatch):
    monkeypatch.setenv("TELEGRAM_ALLOWED_CHATS", "123,456")
    assert telegram_bot._chat_allowed("123")
    assert not telegram_bot._chat_allowed("999")


def test_audit_failure_does_not_propagate(monkeypatch):
    def fail_snapshot():
        raise OSError("simulated persistence failure")
    monkeypatch.setattr(telegram_bot, "snapshot_telegram_state", fail_snapshot)
    update = {"message": {"chat": {"id": 123}, "from": {"id": 456}}}
    assert telegram_bot._audit(update, "/estado", response="ok") is False


def test_internal_errors_are_translated():
    text = telegram_bot._public_text("BLOCKED_NO_TERRITORIAL_INPUT")
    assert "bloqueo" in text.lower()
    assert "COMPROBACIÓN PENDIENTE" not in text


def test_single_notification_chat_is_a_safe_allowlist_fallback(monkeypatch):
    monkeypatch.delenv("TELEGRAM_ALLOWED_CHATS", raising=False)
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
    assert telegram_bot._chat_allowed("123")
    assert not telegram_bot._chat_allowed("999")


def test_authorization_fails_closed_when_both_chat_settings_are_absent(monkeypatch):
    monkeypatch.delenv("TELEGRAM_ALLOWED_CHATS", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    assert not telegram_bot._chat_allowed("123")


def test_authorized_start_sends_useful_briefing(monkeypatch, tmp_path):
    monkeypatch.setenv("TELEGRAM_ALLOWED_CHATS", "123")
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.setattr(telegram_bot, "USER_STATE", tmp_path / "user-state.json")
    monkeypatch.setattr(telegram_bot, "_audit", lambda *args, **kwargs: True)
    monkeypatch.setattr(telegram_bot, "_preferences", lambda update: {"frequency": "daily"})
    calls = []
    monkeypatch.setattr(
        telegram_bot, "_api",
        lambda method, **kwargs: calls.append((method, kwargs)) or {"ok": True},
    )
    update = {
        "update_id": 101,
        "message": {
            "chat": {"id": 123, "type": "private"},
            "from": {"id": 456},
            "text": "/start",
        },
    }

    assert telegram_bot._handle_update(update, None) == 102
    messages = [
        kwargs["json"]["text"]
        for method, kwargs in calls
        if method == "sendMessage" and "json" in kwargs
    ]
    assert messages
    assert any("SALA DE SITUACIÓN" in message for message in messages)


def test_unauthorized_start_is_denied_without_briefing(monkeypatch):
    monkeypatch.setenv("TELEGRAM_ALLOWED_CHATS", "123")
    calls = []
    monkeypatch.setattr(
        telegram_bot, "_api",
        lambda method, **kwargs: calls.append((method, kwargs)) or {"ok": True},
    )
    update = {
        "update_id": 102,
        "message": {
            "chat": {"id": 999, "type": "private"},
            "from": {"id": 888},
            "text": "/start",
        },
    }

    assert telegram_bot._handle_update(update, None) == 103
    messages = [
        kwargs["json"]["text"]
        for method, kwargs in calls
        if method == "sendMessage" and "json" in kwargs
    ]
    assert len(messages) == 1
    assert "no está autorizado" in messages[0].lower()
    assert "SALA DE SITUACIÓN" not in messages[0]


def test_transport_error_never_discloses_bot_token(monkeypatch):
    token = "123456:TEST_SECRET_TOKEN"
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", token)
    monkeypatch.setattr(telegram_bot.time, "sleep", lambda _seconds: None)

    def fail_request(*args, **kwargs):
        raise telegram_bot.requests.ConnectionError(
            f"connection failed for https://api.telegram.org/bot{token}/getUpdates"
        )

    monkeypatch.setattr(telegram_bot.requests, "post", fail_request)
    try:
        telegram_bot._api("getUpdates")
    except telegram_bot.TelegramBotError as exc:
        assert token not in str(exc)
        assert "transport failed" in str(exc).lower()
    else:
        raise AssertionError("failed transport must raise TelegramBotError")
