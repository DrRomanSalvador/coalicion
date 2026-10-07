#!/usr/bin/env python3
"""CLI del Decision Engine de Coaliciones."""
from __future__ import annotations
import argparse, json
from datetime import datetime, timezone
from pathlib import Path
from src.coalition_decision_engine import CoalitionDecisionEngine, CoalitionScenario

def main():
    p=argparse.ArgumentParser(description="Decision Engine de Coaliciones")
    p.add_argument("--input", required=True)
    p.add_argument("--parties", nargs="+", required=True)
    p.add_argument("--min-size", type=int, default=2)
    p.add_argument("--max-size", type=int, default=None)
    p.add_argument("--max-combinations", type=int, default=100000)
    p.add_argument("--output", default=None)
    a=p.parse_args()
    d=json.loads(Path(a.input).read_text(encoding="utf-8"))
    scenarios=[CoalitionScenario(s["name"],s["votes"],float(s.get("weight",1)),
                                 tuple(s.get("assumptions",())),s.get("source","input_dataset"))
               for s in d["scenarios"]]
    e=CoalitionDecisionEngine(d["seats"],d.get("blank"),d.get("special"))
    result=e.analyze_all_coalitions(a.parties,scenarios,a.min_size,a.max_size,a.max_combinations)
    payload={"schema":"COALITION_DECISION_ENGINE_V1",
             "generated_at":datetime.now(timezone.utc).isoformat(),
             "parties_universe":a.parties,"result":result}
    if a.output:
        q=Path(a.output); q.parent.mkdir(parents=True,exist_ok=True)
        q.write_text(json.dumps(payload,ensure_ascii=False,indent=2,sort_keys=True),encoding="utf-8")
    print(json.dumps(payload,ensure_ascii=False,indent=2,sort_keys=True))

if __name__=="__main__":
    main()
