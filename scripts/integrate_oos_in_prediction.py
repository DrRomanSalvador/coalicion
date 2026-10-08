#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import argparse, json
from pathlib import Path
from src.oos_pipeline import load_poll_observations, run_oos


def main():
    ap=argparse.ArgumentParser(description="Integra selección OOS al contrato de predicción")
    ap.add_argument("--input",default="artifacts/data/cis_historical_2004_2023.csv")
    ap.add_argument("--output")
    a=ap.parse_args()
    rows=load_poll_observations(a.input)
    result=run_oos(rows)
    result["prediction_contract"]="USE_SELECTED_CORRECTION_ONLY_IF_OOS_DOMINATES"
    text=json.dumps(result,ensure_ascii=False,indent=2)
    if a.output:
        Path(a.output).parent.mkdir(parents=True,exist_ok=True)
        Path(a.output).write_text(text,encoding="utf-8")
    print(text)


if __name__=="__main__":
    main()
