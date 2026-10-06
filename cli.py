#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from src.data_pipeline import download_workbook, inspect_workbook, load_rows, write_json
from src.decision_engine import coalition_result
from src.marginality import marginal_seat

def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def _canonical(data):
    if "constituencies" in data:
        return data
    raise ValueError("El input debe contener 'constituencies'")

def main():
    parser = argparse.ArgumentParser(prog="coalicion")
    sub = parser.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("download", help="Descarga el dataset oficial del Congreso")
    d.add_argument("--output", default="data/raw/Elecciones-Congreso.xlsx")

    i = sub.add_parser("inspect", help="Muestra hojas y cabeceras")
    i.add_argument("file", default="data/raw/Elecciones-Congreso.xlsx", nargs="?")

    n = sub.add_parser("normalize", help="Normaliza filas provinciales/candidatura")
    n.add_argument("file", default="data/raw/Elecciones-Congreso.xlsx", nargs="?")
    n.add_argument("--output", default="data/processed/congress_rows.json")

    c = sub.add_parser("coalition", help="Calcula el efecto de una coalición")
    c.add_argument("--input", required=True)
    c.add_argument("--parties", nargs="+", required=True)

    m = sub.add_parser("marginal", help="Calcula el escaño marginal por circunscripción")
    m.add_argument("--input", required=True)

    args = parser.parse_args()
    if args.cmd == "download":
        print(download_workbook(args.output))
    elif args.cmd == "inspect":
        print(json.dumps(inspect_workbook(args.file), ensure_ascii=False, indent=2))
    elif args.cmd == "normalize":
        print(write_json(load_rows(args.file), args.output))
    elif args.cmd == "coalition":
        d = _canonical(_load(args.input))
        v = {c:x["votes"] for c,x in d["constituencies"].items()}
        s = {c:x["seats"] for c,x in d["constituencies"].items()}
        valid = {c:x.get("valid_votes",sum(x["votes"].values())+x.get("blank_votes",0)) for c,x in d["constituencies"].items()}
        blank = {c:x.get("blank_votes",0) for c,x in d["constituencies"].items()}
        print(json.dumps(coalition_result(v,s,valid,tuple(args.parties),blank=blank),ensure_ascii=False,indent=2))
    elif args.cmd == "marginal":
        d = _canonical(_load(args.input))
        out={}
        for c,x in d["constituencies"].items():
            out[c]=marginal_seat(x["votes"],x["seats"],x.get("blank_votes",0),x.get("special",""))
        print(json.dumps(out,ensure_ascii=False,indent=2))

if __name__ == "__main__":
    main()
