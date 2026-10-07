#!/usr/bin/env python3
"""Fail-closed survey watcher with deterministic change detection and alerts."""
from __future__ import annotations
import hashlib, json, urllib.request
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

def fetch(url: str) -> bytes:
    req=urllib.request.Request(url,headers={"User-Agent":"coalicion-neutral-survey-watch/2.0"})
    with urllib.request.urlopen(req,timeout=30) as resp:
        return resp.read()

def main():
    cfg=load(CONFIG,{})
    tz=ZoneInfo(cfg.get("timezone","Europe/Madrid"))
    now=datetime.now(timezone.utc).astimezone(tz)
    if now.hour != int(cfg.get("daily_local_hour",8)):
        print(json.dumps({"status":"SKIPPED","reason":"OUTSIDE_DAILY_LOCAL_WINDOW","local_time":now.isoformat()}))
        return 0

    state=load(STATE,{"seen":{},"history":[]})
    events=[]
    for src in cfg.get("sources",[]):
        key=src.get("id") or src.get("url")
        url=src.get("url")
        if not key or not url:
            events.append({"severity":"CRITICAL","status":"INVALID_SOURCE_CONFIG","source_id":key})
            continue
        try:
            body=fetch(url)
            digest=sha256(body)
            previous=state["seen"].get(key)
            if previous == digest:
                events.append({"severity":"INFO","status":"UNCHANGED","source_id":key,"sha256":digest})
                continue
            INBOX.mkdir(parents=True,exist_ok=True)
            target=INBOX/(digest+".source")
            target.write_bytes(body)
            status="NEW_SOURCE_RECORD" if previous is None else "CHANGED_SOURCE_RECORD"
            severity="INFO" if previous is None else "ALERT"
            event={"severity":severity,"status":status,"source_id":key,"sha256":digest,
                   "previous_sha256":previous,"path":str(target.relative_to(ROOT)),
                   "detected_at":now.isoformat()}
            events.append(event)
            state["seen"][key]=digest
            state["history"].append(event)
        except Exception as exc:
            events.append({"severity":"CRITICAL","status":"BLOCKED_SOURCE_FETCH",
                           "source_id":key,"error":str(exc),"detected_at":now.isoformat()})

    blocked=any(e["severity"]=="CRITICAL" for e in events)
    changed=[e for e in events if e["status"]=="CHANGED_SOURCE_RECORD"]
    payload={
      "schema":"SURVEY_WATCH_REPORT_V2",
      "status":"BLOCKED" if blocked else ("ALERT" if changed else "READY"),
      "checked_at":now.isoformat(),
      "alerts":events,
      "alert_count":sum(e["severity"] in {"ALERT","CRITICAL"} for e in events),
      "new_or_changed_sources":len([e for e in events if e["status"] in {"NEW_SOURCE_RECORD","CHANGED_SOURCE_RECORD"}]),
      "scenario_sets":cfg.get("scenario_sets",[]),
      "policy":cfg.get("comparison_policy",{}),
      "report_policy":cfg.get("report_policy",{})
    }
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    STATE.parent.mkdir(parents=True,exist_ok=True)
    STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,ensure_ascii=False))
    return 1 if blocked else 0

if __name__=="__main__":
    raise SystemExit(main())
