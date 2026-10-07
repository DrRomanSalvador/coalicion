"""Telegram notifier with dynamic private-chat resolution."""
from __future__ import annotations
import json, os
from typing import Any
import requests

def resolve_private_chat(session: requests.Session | None = None) -> dict[str, Any] | None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        return None
    session = session or requests.Session()
    response = session.get(
        f"https://api.telegram.org/bot{token}/getUpdates",
        params={"limit": 100, "allowed_updates": json.dumps(["message"])},
        timeout=10,
    )
    response.raise_for_status()
    candidates = []
    for update in response.json().get("result", []):
        message = update.get("message") or {}
        chat = message.get("chat") or {}
        sender = message.get("from") or {}
        if chat.get("type") == "private" and chat.get("id") is not None:
            candidates.append((int(update.get("update_id", 0)), int(chat["id"]), sender))
    if not candidates:
        return None
    update_id, chat_id, sender = max(candidates, key=lambda x: x[0])
    return {"update_id": update_id, "chat_id": chat_id,
            "user_id": sender.get("id"), "username": sender.get("username")}

def send_message(text: str, session: requests.Session | None = None) -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        return False
    session = session or requests.Session()
    destination = resolve_private_chat(session)
    if not destination:
        return False
    response = session.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": str(destination["chat_id"]), "text": text[:4090]},
        timeout=10,
    )
    response.raise_for_status()
    return True

__all__ = ["resolve_private_chat", "send_message"]
