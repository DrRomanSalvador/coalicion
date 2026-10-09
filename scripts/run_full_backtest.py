#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path


def main():
    ap=argparse.ArgumentParser(description="Backtest exhaustivo fail-closed")
    ap.add_argument("--oos-input",default="artifacts/data/cis_historical_2004_2023.csv")
    ap.add_argument("--output",default="artifacts/verification/full_backtest.json")
    a=ap.parse_args()
    commands=[
        [sys.executable,"scripts/backtest_2023_baseline.py"],
        [sys.executable,"scripts/run_full_oos.py","--input",a.oos_input],
    ]
    results=[]
    for cmd in commands:
        p=subprocess.run(cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        results.append({"command":cmd,"returncode":p.returncode,"output":p.stdout[-12000:]})
        if p.returncode:
            Path(a.output).parent.mkdir(parents=True,exist_ok=True)
            Path(a.output).write_text(json.dumps({"status":"BLOCKED","results":results},ensure_ascii=False,indent=2),encoding="utf-8")
            raise SystemExit(p.returncode)
    Path(a.output).parent.mkdir(parents=True,exist_ok=True)
    Path(a.output).write_text(json.dumps({"status":"PASS","results":results},ensure_ascii=False,indent=2),encoding="utf-8")
    print(Path(a.output).read_text(encoding="utf-8"))


if __name__=="__main__":
    main()
