"""Neutral Telegram command bot for the canonical COALICIÓN pipeline.

The bot is deliberately fail-closed:
- it replies to the chat that issued the command;
- it never invents polls, seats, probabilities, MAE or coverage;
- seat projections are shown only from an explicit materialized decision snapshot;
- polling observations are read from the repository's persisted monitor state.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "artifacts" / "poll_monitor_state.json"
SNAPSHOT = ROOT / "artifacts" / "decision_snapshot.json"
API_TIMEOUT = 20


class TelegramBotError(RuntimeError):
    """Raised for configuration or Telegram API failures."""


def _token() -> str:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise TelegramBotError("TELEGRAM_BOT_TOKEN is required")
    if token == "TU_TOKEN_AQUI":
        raise TelegramBotError("placeholder Telegram token is not allowed")
    return token


def _api(method: str, **kwargs: Any) -> dict[str, Any]:
    response = requests.post(
        f"https://api.telegram.org/bot{_token()}/{method}",
        timeout=API_TIMEOUT,
        **kwargs,
    )
    response.raise_for_status()
    payload = response.json()
    if not payload.get("ok"):
        raise TelegramBotError(f"Telegram API error: {payload}")
    return payload


def send_message(chat_id: int, text: str) -> None:
    _api("sendMessage", json={"chat_id": chat_id, "text": text[:4090]})


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _latest_polls() -> list[dict[str, Any]]:
    state = _load_json(STATE) or {}
    rows = state.get("validated_polls") or state.get("polls") or []
    if not isinstance(rows, list):
        return []
    return [x for x in rows if isinstance(x, dict)]


def _prediction_text() -> str:
    snapshot = _load_json(SNAPSHOT)
    if not snapshot:
        return (
            "PREDICCIÓN: BLOQUEADA\n"
            "No existe un snapshot territorial materializado. "
            "No se convierte una encuesta nacional en escaños por inferencia."
        )
    projection = snapshot.get("projection", {})
    seats = projection.get("national_seats") or projection.get("party") or {}
    if not isinstance(seats, dict) or not seats:
        return "PREDICCIÓN: BLOQUEADA\nEl snapshot no contiene escaños nacionales verificables."
    rows = sorted(
        ((str(p), int(v)) for p, v in seats.items()),
        key=lambda x: (-x[1], x[0]),
    )
    return "PROYECCIÓN OBSERVADA\n" + "\n".join(f"{p}: {s}" for p, s in rows)


def _polls_text() -> str:
    polls = _latest_polls()
    if not polls:
        return "ENCUESTAS: sin observaciones validadas materializadas."
    rows = []
    for poll in sorted(
        polls,
        key=lambda x: str(x.get("publication_date", "")),
        reverse=True,
    )[:10]:
        parties = poll.get("parties") or {}
        if not isinstance(parties, dict):
            continue
        values = ", ".join(
            f"{p} {float(v):.1f}%"
            for p, v in sorted(parties.items(), key=lambda x: (-float(x[1]), str(x[0])))[:8]
        )
        rows.append(
            f"{poll.get('publication_date', '?')} · "
            f"{poll.get('pollster', poll.get('source_id', '?'))}: {values}"
        )
    return "ÚLTIMAS OBSERVACIONES VALIDADAS\n" + "\n".join(rows)


def _status_text() -> str:
    state = _load_json(STATE) or {}
    return (
        "ESTADO COALICIÓN\n"
        f"estado: {state.get('status', 'UNKNOWN')}\n"
        f"encuestas validadas: {len(_latest_polls())}\n"
        f"fuentes: {len(state.get('sources') or []) if isinstance(state.get('sources'), list) else 'n/d'}\n"
        "política: fail-closed; sin datos sintéticos"
    )


def render_command(command: str) -> str:
    command = command.split("@", 1)[0].strip().lower()
    if command in {"/start", "/ayuda", "/help"}:
        return (
            "COALICIÓN · vigilancia electoral neutral\n\n"
            "/prediccion — proyección solo si existe snapshot territorial\n"
            "/encuestas — últimas observaciones validadas\n"
            "/estado — estado del monitor\n"
            "/ayuda — ayuda"
        )
    if command == "/prediccion":
        return _prediction_text()
    if command == "/encuestas":
        return _polls_text()
    if command == "/estado":
        return _status_text()
    return "Comando no reconocido. Usa /ayuda."


def poll_once(offset: int | None = None) -> int | None:
    params: dict[str, Any] = {"timeout": 0, "allowed_updates": ["message"]}
    if offset is not None:
        params["offset"] = offset
    payload = _api("getUpdates", params=params)
    updates = payload.get("result") or []
    next_offset = offset
    for update in updates:
        if not isinstance(update, dict):
            continue
        update_id = update.get("update_id")
        if isinstance(update_id, int):
            next_offset = update_id + 1
        message = update.get("message") or {}
        chat = message.get("chat") or {}
        text = str(message.get("text") or "").strip()
        chat_id = chat.get("id")
        if chat_id is None or not text.startswith("/"):
            continue
        send_message(int(chat_id), render_command(text.split()[0]))
    return next_offset


def run_polling(*, poll_timeout: int = 25, sleep_seconds: float = 1.0) -> None:
    """Long-poll Telegram and always answer the initiating chat ID."""
    _token()
    offset: int | None = None
    while True:
        params: dict[str, Any] = {"timeout": poll_timeout, "allowed_updates": ["message"]}
        if offset is not None:
            params["offset"] = offset
        payload = _api("getUpdates", params=params)
        for update in payload.get("result") or []:
            if not isinstance(update, dict):
                continue
            update_id = update.get("update_id")
            if isinstance(update_id, int):
                offset = update_id + 1
            message = update.get("message") or {}
            chat_id = (message.get("chat") or {}).get("id")
            text = str(message.get("text") or "").strip()
            if chat_id is not None and text.startswith("/"):
                send_message(int(chat_id), render_command(text.split()[0]))
        if sleep_seconds:
            time.sleep(sleep_seconds)


if __name__ == "__main__":
    run_polling()
