"""Telegram notifier with explicit, fail-closed destinations.

The notifier never calls getUpdates. The long-polling bot is the sole consumer
of incoming updates; scheduled notifications use the configured allowlist.
"""
from __future__ import annotations

import os
from typing import Any
import requests


def _allowed_chats() -> list[str]:
    raw = os.environ.get("TELEGRAM_ALLOWED_CHATS", "").strip()
    return [x.strip() for x in raw.split(",") if x.strip()]


def resolve_private_chat(session: requests.Session | None = None) -> dict[str, Any] | None:
    chats = _allowed_chats()
    if not chats:
        return None
    return {"chat_id": int(chats[0]), "source": "TELEGRAM_ALLOWED_CHATS"}


def send_message(text: str, session: requests.Session | None = None) -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        return False
    destination = resolve_private_chat(session)
    if not destination:
        return False
    session = session or requests.Session()
    response = session.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": str(destination["chat_id"]), "text": text[:4090]},
        timeout=10,
    )
    response.raise_for_status()
    return True


__all__ = ["resolve_private_chat", "send_message"]
