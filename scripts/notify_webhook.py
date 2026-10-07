#!/usr/bin/env python3
"""Fail-closed Telegram Bot API notifier. Secrets are never stored in the repository."""
from __future__ import annotations
import json, os, sys, urllib.parse, urllib.request

def send(text: str) -> dict:
    token=os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id=os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise RuntimeError("BLOCKED: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required")
    url=f"https://api.telegram.org/bot{token}/sendMessage"
    data=urllib.parse.urlencode({
        "chat_id":chat_id,
        "text":text[:4090],
        "disable_web_page_preview":"true",
    }).encode()
    req=urllib.request.Request(url,data=data,headers={"User-Agent":"coalicion-neutral-telegram/1.0"})
    with urllib.request.urlopen(req,timeout=20) as response:
        result=json.loads(response.read().decode())
    if not result.get("ok"):
        raise RuntimeError("BLOCKED: Telegram rejected sendMessage")
    return result

def format_report(report: dict) -> str:
    lines=["🔔 Colmena neutral — "+str(report.get("status","UNKNOWN")),
           "Comprobado: "+str(report.get("checked_at","")),
           "Alertas: "+str(report.get("alert_count",0))]
    for event in report.get("alerts",[]):
        if event.get("severity") in {"ALERT","CRITICAL"}:
            lines.append(f"{event.get('severity')}: {event.get('status')} — {event.get('source_id','')}")
            poll=event.get("poll")
            if poll:
                lines.append(f"Encuesta: {poll.get('pollster','')} · {poll.get('publication_date','')}")
    if report.get("report_path"):
        lines.append("Informe: "+str(report["report_path"]))
    return "\n".join(lines)

if __name__=="__main__":
    path=sys.argv[1] if len(sys.argv)>1 else "artifacts/survey_watch_report.json"
    with open(path,encoding="utf-8") as fh: report=json.load(fh)
    print(json.dumps(send(format_report(report)),ensure_ascii=False))
