#!/usr/bin/env python3
"""Generic JSON webhook notifier; the endpoint stays in a GitHub Actions secret."""
from __future__ import annotations
import json, os, sys, urllib.request

def send(payload: dict) -> dict:
    endpoint = os.environ.get("NOTIFY_WEBHOOK_URL")
    if not endpoint:
        raise RuntimeError("BLOCKED: NOTIFY_WEBHOOK_URL is required")
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(endpoint, data=body,
        headers={"Content-Type":"application/json",
                 "User-Agent":"coalicion-neutral-notifier/1.0"})
    with urllib.request.urlopen(req, timeout=20) as response:
        return {"status": response.status, "body": response.read().decode("utf-8")[:1000]}

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "artifacts/survey_watch_report.json"
    report = json.load(open(path, encoding="utf-8"))
    message = {
        "text": "Colmena neutral — {} — alertas: {}".format(
            report.get("status", "UNKNOWN"), report.get("alert_count", 0)),
        "report": report,
    }
    print(json.dumps(send(message), ensure_ascii=False))
