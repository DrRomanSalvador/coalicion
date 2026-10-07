#!/usr/bin/env python3
"""Fetch configured poll sources and detect new or changed polls."""
from __future__ import annotations
import hashlib,json,sys,urllib.request
from datetime import datetime,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.poll_ingest import parse_source,canonical_poll,poll_hash
CONFIG=ROOT/"config/survey_watch.json"; STATE=ROOT/"artifacts/poll_vigilance_state.json"; REPORT=ROOT/"artifacts/poll_vigilance_report.json"; INBOX=ROOT/"artifacts/surveys"

def load(p,d): return json.loads(p.read_text(encoding="utf-8")) if p.exists() else d

def fetch(url):
    req=urllib.request.Request(url,headers={"User-Agent":"coalicion-poll-vigilance/1.0"})
    with urllib.request.urlopen(req,timeout=30) as r: return r.read()

def main():
    cfg=load(CONFIG,{})
    tz=ZoneInfo(cfg.get("timezone","Europe/Madrid"))
    now=datetime.now(timezone.utc).astimezone(tz)
    state=load(STATE,{"seen_sources":{},"seen_polls":{},"baseline_completed":False})
    state.setdefault("seen_sources",{})
    state.setdefault("seen_polls",{})
    baseline=not state.get("baseline_completed",False) and not state["seen_polls"]
    events=[]
    discovered_only=0
    for source in cfg.get("sources",[]):
        sid=source.get("id") or source.get("url")
        try:
            body=fetch(source["url"]); digest=hashlib.sha256(body).hexdigest()
            INBOX.mkdir(parents=True,exist_ok=True); (INBOX/(digest+".source")).write_bytes(body)
            for poll in parse_source(body,source):
                h=poll_hash(poll)
                old=state["seen_polls"].get(poll.poll_id)
                state["seen_polls"][poll.poll_id]=h
                # RSS/discovery entries without party-level values are tracked
                # for deduplication but are never presented as new surveys.
                if source.get("discovery_only") or not poll.parties:
                    discovered_only += 1
                    continue
                if old == h:
                    continue
                if baseline:
                    continue
                events.append({
                    "status":"NEW_POLL" if old is None else "CHANGED_POLL",
                    "source_id":sid,
                    "poll":canonical_poll(poll),
                    "poll_hash":h,
                    "previous_poll_hash":old,
                })
            state["seen_sources"][sid]=digest
        except Exception as exc:
            events.append({"status":"BLOCKED_SOURCE","source_id":sid,"error":str(exc)})
    state["baseline_completed"]=True
    status="ALERT" if any(e["status"] in {"NEW_POLL","CHANGED_POLL"} for e in events) else (
        "BLOCKED" if any(e["status"]=="BLOCKED_SOURCE" for e in events) else "READY"
    )
    payload={
        "schema":"POLL_VIGILANCE_V2",
        "checked_at":now.isoformat(),
        "status":status,
        "baseline_initialized":baseline,
        "discovery_only_count":discovered_only,
        "new_poll_count":sum(e["status"]=="NEW_POLL" for e in events),
        "changed_poll_count":sum(e["status"]=="CHANGED_POLL" for e in events),
        "events":events,
        "scenario_sets":cfg.get("scenario_sets",[]),
        "descriptive_only":True,
    }
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,ensure_ascii=False))
    return 1 if payload["status"]=="BLOCKED" else 0

if __name__=="__main__": raise SystemExit(main())
