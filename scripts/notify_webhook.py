#!/usr/bin/env python3
"""Secret-backed Telegram-compatible webhook notifier."""
from __future__ import annotations
import json, os, sys, urllib.request

def send(text: str) -> dict:
    endpoint=os.environ.get("NOTIFY_WEBHOOK_URL")
    chat_id=os.environ.get("TELEGRAM_CHAT_ID")
    if not endpoint or not chat_id:
        raise RuntimeError("BLOCKED: notification secrets are required")
    payload={"chat_id":chat_id,"text":text[:4090],"disable_web_page_preview":True}
    req=urllib.request.Request(endpoint,data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type":"application/json","User-Agent":"coalicion-neutral-notifier/1.0"})
    with urllib.request.urlopen(req,timeout=20) as response:
        result=json.loads(response.read().decode("utf-8"))
    if result.get("ok") is False:
        raise RuntimeError("BLOCKED: notification endpoint rejected the message")
    return result

if __name__=="__main__":
    path=sys.argv[1] if len(sys.argv)>1 else "artifacts/survey_watch_report.json"
    report=json.load(open(path,encoding="utf-8"))
    lines=["Colmena neutral — "+str(report.get("status","UNKNOWN")),
           "Comprobado: "+str(report.get("checked_at","")),
           "Alertas: "+str(report.get("alert_count",0))]
    for e in report.get("alerts",[]):
        if e.get("severity") in {"ALERT","CRITICAL"}:
            lines.append("{}: {} — {}".format(e.get("severity"),e.get("status"),e.get("source_id","")))
            poll=e.get("poll")
            if poll:
                lines.append("Encuesta: {} {}".format(poll.get("pollster",""),poll.get("publication_date","")))
    if report.get("report_path"): lines.append("Informe: "+str(report["report_path"]))
    print(json.dumps(send("\n".join(lines)),ensure_ascii=False))
