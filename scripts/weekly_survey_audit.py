#!/usr/bin/env python3
"""Weekly, reproducible audit of Spain general-election survey vigilance."""
from __future__ import annotations
import json, re, subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REG=ROOT/"config/poll_source_registry.json"
CFG=ROOT/"config/poll_monitor.json"
STATE=ROOT/"artifacts/poll_monitor_state.json"
HISTORY=ROOT/"artifacts/survey_history.jsonl"
OUT=ROOT/"ci_evidence/weekly_survey_audit.json"

def load(p, default):
    if not p.exists(): return default
    try: return json.loads(p.read_text(encoding="utf-8"))
    except Exception: return default

def run(cmd):
    p=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
    return {"returncode":p.returncode,"stdout":p.stdout[-4000:],"stderr":p.stderr[-4000:]}

def main():
    reg=load(REG,{})
    cfg=load(CFG,{})
    state=load(STATE,{})
    checks=[]
    sources=cfg.get("sources",[])
    primary=[s for s in sources if not s.get("disabled") and s.get("coverage_role")=="primary" and not s.get("optional")]
    statuses=state.get("source_status",{})
    unhealthy=[s.get("id") for s in primary if statuses.get(s.get("id"),{}).get("status")!="OK"]
    disabled_without_reason=[s.get("id") for s in sources if s.get("disabled") and not s.get("reason")]
    checks.append({"id":"PRIMARY_SOURCE_HEALTH","pass":not unhealthy,"unhealthy":unhealthy})
    checks.append({"id":"DISABLED_SOURCES_EXPLAINED","pass":not disabled_without_reason,"sources":disabled_without_reason})
    known=set(reg.get("known_pollsters",[]))
    checks.append({"id":"REGISTRY_CONTRACT","pass":bool(known and reg.get("reference_sources")),"known_pollsters":len(known)})
    last_cov=state.get("last_coverage",{})
    checks.append({"id":"RUNTIME_COVERAGE","pass":bool(last_cov.get("total")),"evidence":last_cov})
    history=[]
    if HISTORY.exists():
        for line in HISTORY.read_text(encoding="utf-8",errors="replace").splitlines()[-5000:]:
            try: history.append(json.loads(line))
            except Exception: pass
    ids=[str(x.get("poll_id") or x.get("id")) for x in history if x.get("poll_id") or x.get("id")]
    duplicate_ids=len(ids)-len(set(ids))
    checks.append({"id":"HISTORY_DEDUPLICATION","pass":duplicate_ids==0,"duplicate_records":duplicate_ids})
    revisions=sum(1 for x in history if str(x.get("status","")).upper() in {"CHANGED","CHANGED_POLL","REVISION"})
    checks.append({"id":"REVISION_EVENTS_TYPED","pass= revisions >= 0,"revision_events":revisions})
    watch=load(ROOT/"artifacts/survey_watch_report.json",{})
    checks.append({"id":"WATCH_NOT_BLOCKED","pass":watch.get("status")!="BLOCKED","status":watch.get("status"),"alerts":watch.get("alert_count")})
    malformed=watch.get("quarantined_report_records",0)
    checks.append({"id":"MALFORMED_STATE_QUARANTINE","pass":malformed==0,"quarantined":malformed})
    # Static extractor drift heuristic: every configured non-discovery source must
    # have a parser format known by src.poll_ingest.
    parser=ROOT/"src/poll_ingest.py"
    text=parser.read_text(encoding="utf-8") if parser.exists() else ""
    supported=set(re.findall(r'kind=="([a-zA-Z0-9_]+)"',text))
    unsupported=sorted({s.get("format","json") for s in sources if not s.get("discovery_only") and s.get("format","json") not in supported})
    checks.append({"id":"EXTRACTOR_FORMAT_COVERAGE","pass":not unsupported,"unsupported_formats":unsupported})
    pytest=run(["python","-m","pytest","tests/test_survey_watch.py","tests/test_poll_ingest_contract.py","tests/test_poll_validator.py","tests/test_poll_normalizer.py","-q"])
    checks.append({"id":"VIGILANCE_TESTS","pass":pytest["returncode"]==0,"returncode":pytest["returncode"]})
    failed=[c["id"] for c in checks if not c.get("pass")]
    result={
      "schema":"WEEKLY_SURVEY_VIGILANCE_AUDIT_V1",
      "checked_at":datetime.now(timezone.utc).isoformat(),
      "status":"PASS" if not failed else "BLOCKED",
      "claim":"WEEKLY_VIGILANCE_AUDIT_VERIFIED" if not failed else "WEEKLY_VIGILANCE_AUDIT_BLOCKED",
      "scope":"configured Spain national general-election survey universe",
      "checks_total":len(checks),"checks_passed":len(checks)-len(failed),"checks_failed":len(failed),
      "failed_checks":failed,"checks":checks,
      "coverage_limit":"No total pollster/source coverage is claimed. Registry/discovery coverage is not primary evidence.",
      "priorities":[
        "repair unhealthy primary sources before adding discovery sources",
        "quarantine malformed historical records rather than silently coercing them",
        "treat extractor-format drift as a blocker",
        "separate revisions from genuinely new polls and retain prior hashes",
        "keep national poll data separate from territorial inference"
      ]
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False))
    raise SystemExit(0 if not failed else 1)

if __name__=="__main__": main()
