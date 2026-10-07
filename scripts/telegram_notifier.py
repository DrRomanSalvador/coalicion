#!/usr/bin/env python3
"""Send neutral new-poll alerts through the Telegram Bot API."""
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
                total = sum(float(parties.get(p, 0)) for p in coalition)
                lines.append(f"{' + '.join(coalition)}: {total:g}%")
    lines += ["", "Análisis descriptivo; sin recomendaciones ni ranking de coaliciones."]
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
        description = payload.get("description") or f"HTTP {exc.code}"
        raise RuntimeError(
            f"BLOCKED: Telegram {method} rejected the request: "
            f"HTTP {exc.code}: {description}"
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


def send(text):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise RuntimeError("BLOCKED: Telegram secrets are required")

    # getMe validates the bot token and lets us reject the common mistake
    # of configuring the bot's own user id as the destination chat.
    bot = _telegram_request(token, "getMe")
    bot_id = str(bot.get("id", ""))
    if chat_id == bot_id:
        # Resolve the real private chat from the user's /start update.
        # This avoids requiring an external user-info bot.
        target_username = os.environ.get(
            "TELEGRAM_TARGET_USERNAME", "DrRomanSalvador"
        ).lstrip("@").lower()
        updates = _telegram_request(
            token,
            "getUpdates",
            {"limit": "20", "allowed_updates": json.dumps(["message"])},
        )
        candidates = []
        for update in updates:
            message = update.get("message") or {}
            chat = message.get("chat") or {}
            user = message.get("from") or {}
            if chat.get("type") != "private":
                continue
            username = str(user.get("username") or chat.get("username") or "").lower()
            if username == target_username and chat.get("id") is not None:
                candidates.append(str(chat["id"]))
        if not candidates:
            raise RuntimeError(
                "BLOCKED: Telegram bot is configured as the destination and "
                f"no private chat update was found for @{target_username}. "
                "Open the bot, press Start, and send /start again."
            )
        chat_id = candidates[-1]
        print(
            f"Telegram destination resolved from @{target_username}: "
            f"private chat id {chat_id}"
        )

    return _telegram_request(
        token,
        "sendMessage",
        {
            "chat_id": chat_id,
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
