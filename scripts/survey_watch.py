#!/usr/bin/env python3
"""Daily fail-closed poll watcher: fetch, validate, normalize, diff, report, alert."""
from __future__ import annotations
import hashlib, json, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.poll_ingest import parse_source, canonical_poll, poll_hash
CONFIG=ROOT/"config/survey_watch.json"; STATE=ROOT/"artifacts/survey_watch_state.json"
INBOX=ROOT/"artifacts/surveys"; REPORT=ROOT/"artifacts/survey_watch_report.json"
POLL_REPORT=ROOT/"artifacts/neutral_poll_report.json"

def sha256(b): return hashlib.sha256(b).hexdigest()
def load(p,d): return json.loads(p.read_text(encoding="utf-8")) if p.exists() else d
def fetch(url):
    req=urllib.request.Request(url,headers={"User-Agent":"coalicion-neutral-survey-watch/3.0"})
    with urllib.request.urlopen(req,timeout=30) as r: return r.read()

def main():
    cfg=load(CONFIG,{})
    tz=ZoneInfo(cfg.get("timezone","Europe/Madrid")); now=datetime.now(timezone.utc).astimezone(tz)
    if now.hour != int(cfg.get("daily_local_hour",8)):
        print(json.dumps({"status":"SKIPPED","reason":"OUTSIDE_DAILY_LOCAL_WINDOW","local_time":now.isoformat()})); return 0
    state=load(STATE,{"seen_sources":{},"seen_polls":{},"history":[]})
    events=[]; canonical=[]
    for src in cfg.get("sources",[]):
        key=src.get("id") or src.get("url")
        if not key or not src.get("url"):
            events.append({"severity":"CRITICAL","status":"INVALID_SOURCE_CONFIG","source_id":key}); continue
        try:
            body=fetch(src["url"]); digest=sha256(body); previous=state["seen_sources"].get(key)
            if previous==digest:
                events.append({"severity":"INFO","status":"UNCHANGED","source_id":key,"sha256":digest}); continue
            INBOX.mkdir(parents=True,exist_ok=True); (INBOX/(digest+".source")).write_bytes(body)
            state["seen_sources"][key]=digest
            if src.get("discovery_only"):
                status="NEW_SOURCE_RECORD" if previous is None else "CHANGED_SOURCE_RECORD"
                severity="INFO" if previous is None else "ALERT"
                events.append({"severity":severity,"status":status,"source_id":key,"sha256":digest,
                                "previous_sha256":previous,"path":str((INBOX/(digest+".source")).relative_to(ROOT)),
                                "detected_at":now.isoformat()})
                continue
            polls=parse_source(body,src)
            for poll in polls:
                h=poll_hash(poll); old=state["seen_polls"].get(poll.poll_id)
                if old==h: continue
                record=canonical_poll(poll); canonical.append(record)
                state["seen_polls"][poll.poll_id]=h
                events.append({"severity":"ALERT" if old else "ALERT","status":"NEW_POLL" if old is None else "CHANGED_POLL",
                                "source_id":key,"poll":record,"poll_hash":h,"previous_poll_hash":old,
                                "detected_at":now.isoformat()})
            if not polls:
                events.append({"severity":"WARNING","status":"NO_POLL_RECORDS","source_id":key,"sha256":digest})
        except Exception as exc:
            events.append({"severity":"CRITICAL","status":"BLOCKED_SOURCE_PARSE_OR_FETCH","source_id":key,
                           "error":str(exc),"detected_at":now.isoformat()})
    poll_events=[e for e in events if e.get("status") in {"NEW_POLL","CHANGED_POLL"}]
    if poll_events:
        poll_payload=json.loads(POLL_REPORT.read_text(encoding="utf-8")) if POLL_REPORT.exists() else {}
        existing=[x.get("poll") for x in poll_payload.get("reports",[]) if x.get("poll")]
        by_id={x["id"]:x for x in existing}
        for e in poll_events: by_id[e["poll"]["id"]]=e["poll"]
        from scripts.build_poll_report import build
        built=build(list(by_id.values()),cfg.get("scenario_sets",[]))
        POLL_REPORT.parent.mkdir(parents=True,exist_ok=True)
        POLL_REPORT.write_text(json.dumps(built,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    blocked=any(e["severity"]=="CRITICAL" for e in events)
    changed=bool(poll_events or any(e["status"]=="CHANGED_SOURCE_RECORD" for e in events))
    payload={"schema":"SURVEY_WATCH_REPORT_V3","status":"BLOCKED" if blocked else ("ALERT" if changed else "READY"),
             "checked_at":now.isoformat(),"alerts":events,
             "alert_count":sum(e["severity"] in {"ALERT","CRITICAL"} for e in events),
             "new_or_changed_polls":len(poll_events),"scenario_sets":cfg.get("scenario_sets",[]),
             "policy":cfg.get("comparison_policy",{}),"report_policy":cfg.get("report_policy",{}),
             "report_path":"artifacts/neutral_poll_report.json" if POLL_REPORT.exists() else None}
    state["history"].extend(events); state["last_checked_at"]=now.isoformat()
    REPORT.parent.mkdir(parents=True,exist_ok=True); REPORT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,ensure_ascii=False)); return 1 if blocked else 0
if __name__=="__main__": raise SystemExit(main())
