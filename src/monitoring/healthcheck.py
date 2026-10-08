"""Health summary derived only from materialized monitor state."""
from __future__ import annotations
import json
from pathlib import Path

def healthcheck(state_path: Path) -> dict:
    if not state_path.is_file():
        return {"status":"BLOCKED","reason":"BLOCKED_MONITOR_STATE_MISSING","fail_closed":True}
    try: data=json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError):
        return {"status":"BLOCKED","reason":"BLOCKED_MONITOR_STATE_INVALID","fail_closed":True}
    sources=data.get("sources",[])
    if not isinstance(sources,list):
        return {"status":"BLOCKED","reason":"BLOCKED_MONITOR_SOURCES_INVALID","fail_closed":True}
    counts={}
    for item in sources:
        status=str(item.get("status",item.get("health","UNKNOWN"))).upper() if isinstance(item,dict) else "UNKNOWN"
        counts[status]=counts.get(status,0)+1
    return {"status":"OK","source_count":len(sources),"source_status":dict(sorted(counts.items())),"fail_closed":True}
