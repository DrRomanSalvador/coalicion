#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, json
from pathlib import Path
from src.probabilistic_calibration import evaluate


def main():
    ap=argparse.ArgumentParser(description="Calibración probabilística OOS")
    ap.add_argument("--input", required=True,
                    help="CSV con actual,probability[,lower,upper]")
    ap.add_argument("--output")
    a=ap.parse_args()
    p=Path(a.input)
    if not p.exists(): raise SystemExit(f"Falta dataset OOS: {p}")
    with p.open(newline="",encoding="utf-8") as fh: rows=list(csv.DictReader(fh))
    if not rows: raise SystemExit("Dataset de calibración vacío")
    required={"actual","probability"}
    if not required <= set(rows[0]): raise SystemExit(f"Faltan columnas: {sorted(required-set(rows[0]))}")
    actual=[int(r["actual"]) for r in rows]
    prob=[float(r["probability"]) for r in rows]
    lo=[float(r.get("lower",0)) for r in rows]
    hi=[float(r.get("upper",1)) for r in rows]
    s=evaluate(actual,prob,lo,hi)
    out={"status":"PASS","n":s.n,"brier":s.brier,"coverage":s.coverage,
         "mean_interval_width":s.mean_interval_width,"reliability":s.reliability}
    text=json.dumps(out,ensure_ascii=False,indent=2)
    if a.output:
        Path(a.output).parent.mkdir(parents=True,exist_ok=True)
        Path(a.output).write_text(text,encoding="utf-8")
    print(text)


if __name__=="__main__":
    main()
