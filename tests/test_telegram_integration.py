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
