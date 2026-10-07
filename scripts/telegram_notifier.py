#!/usr/bin/env python3
"""Send neutral new-poll alerts through the Telegram Bot API."""
from __future__ import annotations
import json,os,sys,urllib.parse,urllib.request
SCENARIOS=(("SUMAR","PODEMOS"),("SUMAR","PSOE"),("SUMAR","PODEMOS","PSOE"))
def build_message(report):
    lines=["🔔 Vigilancia electoral — nueva encuesta"]
    for event in report.get("events",[]):
        if event.get("status") not in {"NEW_POLL","CHANGED_POLL"}: continue
        poll=event["poll"]; lines += ["",f"Estado: {event['status']}",f"Fuente: {poll.get('source_id','')}",f"Encuestadora: {poll.get('pollster','')}",f"Publicación: {poll.get('publication_date','')}"]
        parties=poll.get("parties",{})
        if parties:
            lines.append("Estimación publicada: "+", ".join(f"{k} {v:g}%" for k,v in sorted(parties.items())))
            for coalition in SCENARIOS:
                total=sum(float(parties.get(p,0)) for p in coalition)
                lines.append(f"{' + '.join(coalition)}: {total:g}%")
    lines += ["","Análisis descriptivo; sin recomendaciones ni ranking de coaliciones."]
    return "\n".join(lines)[:4090]
def send(text):
    token=os.environ.get("TELEGRAM_BOT_TOKEN"); chat_id=os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id: raise RuntimeError("BLOCKED: Telegram secrets are required")
    url=f"https://api.telegram.org/bot{token}/sendMessage"; data=urllib.parse.urlencode({"chat_id":chat_id,"text":text,"disable_web_page_preview":"true"}).encode()
    req=urllib.request.Request(url,data=data,headers={"User-Agent":"coalicion-poll-vigilance/1.0"})
    with urllib.request.urlopen(req,timeout=20) as response: result=json.loads(response.read().decode())
    if not result.get("ok"): raise RuntimeError("BLOCKED: Telegram rejected sendMessage")
    return result
def main():
    path=sys.argv[1] if len(sys.argv)>1 else "artifacts/poll_vigilance_report.json"
    report=json.loads(open(path,encoding="utf-8").read())
    if not any(e.get("status") in {"NEW_POLL","CHANGED_POLL"} for e in report.get("events",[])): print("NO_NEW_POLL"); return 0
    print(json.dumps(send(build_message(report)),ensure_ascii=False)); return 0
if __name__=="__main__": raise SystemExit(main())
