#!/usr/bin/env python3
"""Daily fail-closed watcher for explicitly configured polling sources.

The watcher detects new source records and prepares neutral scenario inputs.
It never invents polling figures, party mappings, or recommendations.
"""
from __future__ import annotations
import hashlib, json, sys, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/"config/survey_watch.json"
STATE=ROOT/"artifacts/survey_watch_state.json"
INBOX=ROOT/"artifacts/surveys"
REPORT=ROOT/"artifacts/survey_watch_report.json"

def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def load(p, default):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default

def main():
    cfg=load(CONFIG,{})
    tz=ZoneInfo(cfg.get("timezone","Europe/Madrid"))
    now=datetime.now(timezone.utc).astimezone(tz)
    if now.hour != int(cfg.get("daily_local_hour",8)):
        print(json.dumps({"status":"SKIPPED","reason":"OUTSIDE_DAILY_LOCAL_WINDOW","local_time":now.isoformat()}))
        return 0

    state=load(STATE,{"seen":{}})
    events=[]
    for src in cfg.get("sources",[]):
        url=src.get("url")
        if not url:
            continue
        try:
            req=urllib.request.Request(url,headers={"User-Agent":"coalicion-neutral-survey-watch/1.0"})
            with urllib.request.urlopen(req,timeout=30) as resp:
                body=resp.read()
            digest=sha256(body)
            key=src.get("id",url)
            if state["seen"].get(key)==digest:
                continue
            INBOX.mkdir(parents=True,exist_ok=True)
            target=INBOX/(digest+".source")
            target.write_bytes(body)
            state["seen"][key]=digest
            events.append({"source_id":key,"status":"NEW_SOURCE_RECORD","sha256":digest,"path":str(target.relative_to(ROOT))})
        except Exception as exc:
            events.append({"source_id":src.get("id",url),"status":"BLOCKED_SOURCE_FETCH","error":str(exc)})

    payload={
      "schema":"SURVEY_WATCH_REPORT_V1",
      "status":"READY" if not any(e["status"].startswith("BLOCKED") for e in events) else "BLOCKED",
      "checked_at":now.isoformat(),
      "new_sources":events,
      "scenario_sets":cfg.get("scenario_sets",[]),
      "policy":cfg.get("comparison_policy",{})
    }
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    STATE.parent.mkdir(parents=True,exist_ok=True)
    STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,ensure_ascii=False))
    return 0 if payload["status"]=="READY" else 1

if __name__=="__main__":
    raise SystemExit(main())
