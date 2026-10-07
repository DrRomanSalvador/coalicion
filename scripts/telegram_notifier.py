#!/usr/bin/env python3
"""Send Telegram alerts to the chat that initiated the bot conversation."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

SCENARIOS = (
    ("SUMAR", "PODEMOS"),
    ("SUMAR", "PSOE"),
    ("SUMAR", "PODEMOS", "PSOE"),
)


def build_message(report):
    lines = ["🔔 Vigilancia electoral — nueva encuesta"]
    for event in report.get("events", []):
        if event.get("status") not in {"NEW_POLL", "CHANGED_POLL"}:
            continue
        poll = event["poll"]
        lines += [
            "",
            f"Estado: {event['status']}",
            f"Fuente: {poll.get('source_id', '')}",
            f"Encuestadora: {poll.get('pollster', '')}",
            f"Publicación: {poll.get('publication_date', '')}",
        ]
        parties = poll.get("parties", {})
        if parties:
            lines.append(
                "Estimación publicada: "
                + ", ".join(f"{k} {v:g}%" for k, v in sorted(parties.items()))
            )
            for coalition in SCENARIOS:
                members = [p for p in coalition if p in parties]
                total = sum(float(parties[p]) for p in members)
                lines.append(
                    "Voto nacional conjunto ("
                    + " + ".join(members)
                    + f"): {total:g}%"
                )
            lines.append(
                "Proyección de escaños: BLOQUEADA — "
                "faltan datos territoriales verificables."
            )
    return "\n".join(lines)[:4090]


def _telegram_request(token, method, data=None):
    url = f"https://api.telegram.org/bot{token}/{method}"
    encoded = urllib.parse.urlencode(data or {}).encode()
    req = urllib.request.Request(
        url,
        data=encoded,
        headers={"User-Agent": "coalicion-poll-vigilance/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = {}
        raise RuntimeError(
            f"BLOCKED: Telegram {method} rejected the request: "
            f"HTTP {exc.code}: {payload.get('description', 'unknown error')}"
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"BLOCKED: Telegram {method} connection failed: {exc.reason}"
        ) from exc

    if not payload.get("ok"):
        raise RuntimeError(
            f"BLOCKED: Telegram {method} rejected the request: "
            f"{payload.get('description', 'unknown Telegram error')}"
        )
    return payload["result"]


def resolve_initiating_chat(token):
    """Resolve the private chat from Telegram's incoming message.chat.id."""
    updates = _telegram_request(
        token,
        "getUpdates",
        {"limit": "100", "allowed_updates": json.dumps(["message"])},
    )

    candidates = []
    for update in updates:
        message = update.get("message") or {}
        chat = message.get("chat") or {}
        sender = message.get("from") or {}
        if chat.get("type") != "private":
            continue
        if chat.get("id") is None or sender.get("id") is None:
            continue

        candidates.append(
            {
                "update_id": int(update.get("update_id", 0)),
                "chat_id": int(chat["id"]),
                "user_id": int(sender["id"]),
                "username": sender.get("username"),
                "text": str(message.get("text") or "").strip(),
            }
        )

    if not candidates:
        raise RuntimeError(
            "BLOCKED: no hay conversación privada entrante. "
            "La persona debe abrir el bot y enviar /start."
        )

    starts = [
        item for item in candidates
        if item["text"].split()[0:1] == ["/start"]
    ]
    selected = max(starts or candidates, key=lambda item: item["update_id"])

    print(
        "Telegram destination resolved dynamically: "
        f"user_id={selected['user_id']} chat_id={selected['chat_id']} "
        f"username=@{selected['username'] or 'sin_username'}"
    )
    return selected["chat_id"]


def send(text):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("BLOCKED: TELEGRAM_BOT_TOKEN is required")

    # TELEGRAM_CHAT_ID is optional. If absent, resolve the destination from
    # the incoming Telegram message, never from a hard-coded user id.
    chat_id = os.environ.get("TELEGRAM_CHAT_ID") or resolve_initiating_chat(token)

    return _telegram_request(
        token,
        "sendMessage",
        {
            "chat_id": str(chat_id),
            "text": text,
            "disable_web_page_preview": "true",
        },
    )


def reply_to_update(update, text):
    """Reply to exactly the same chat that produced this incoming update."""
    message = update.get("message") or {}
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    if chat_id is None:
        raise RuntimeError("BLOCKED: incoming Telegram update has no chat.id")

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("BLOCKED: TELEGRAM_BOT_TOKEN is required")

    return _telegram_request(
        token,
        "sendMessage",
        {
            "chat_id": str(chat_id),
            "text": text,
            "disable_web_page_preview": "true",
        },
    )


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "artifacts/poll_vigilance_report.json"
    report = json.loads(open(path, encoding="utf-8").read())
    if not any(
        e.get("status") in {"NEW_POLL", "CHANGED_POLL"}
        for e in report.get("events", [])
    ):
        print("NO_NEW_POLL")
        return 0
    print(json.dumps(send(build_message(report)), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
