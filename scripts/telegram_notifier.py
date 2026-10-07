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

    # getMe validates the bot token separately from the destination chat.
    _telegram_request(token, "getMe")
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
