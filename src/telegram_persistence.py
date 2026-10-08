"""Durable Telegram state snapshot for ephemeral GitHub Actions runners."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "artifacts/telegram_state.json"

STATE_FILES = {
    "config": ROOT / "artifacts/telegram_config.json",
    "user_state": ROOT / "artifacts/telegram_user_state.json",
    "alert_state": ROOT / "artifacts/telegram_alert_state.json",
    "digest_state": ROOT / "artifacts/telegram_digest_state.json",
    "audit_log": ROOT / "artifacts/telegram_audit.jsonl",
}

def _read(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    except (OSError, json.JSONDecodeError):
        return None

def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    tmp.replace(path)

def restore() -> None:
    snapshot = _read(SNAPSHOT)
    if not isinstance(snapshot, dict):
        return
    for key, path in STATE_FILES.items():
        if path.exists():
            continue
        value = snapshot.get(key)
        if value is not None:
            if key == "audit_log":
                path.write_text(str(value), encoding="utf-8")
            else:
                _write(path, value)

def snapshot() -> None:
    payload: dict[str, Any] = {"schema": "TELEGRAM_STATE_V1"}
    for key, path in STATE_FILES.items():
        if key == "audit_log":
            try:
                payload[key] = path.read_text(encoding="utf-8") if path.exists() else ""
            except OSError:
                payload[key] = ""
        else:
            payload[key] = _read(path)
    _write(SNAPSHOT, payload)
