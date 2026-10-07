#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import argparse, json
from src.temporal_decay import exponential_weights


def main():
    ap=argparse.ArgumentParser(description="Genera pesos temporales reproducibles")
    ap.add_argument("--dates", nargs="+", required=True)
    ap.add_argument("--reference-date")
    ap.add_argument("--half-life-days", type=float, default=365.25)
    a=ap.parse_args()
    out={"dates":a.dates,"reference_date":a.reference_date or max(a.dates),
         "half_life_days":a.half_life_days,
         "weights":exponential_weights(a.dates,a.reference_date,a.half_life_days)}
    print(json.dumps(out,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
