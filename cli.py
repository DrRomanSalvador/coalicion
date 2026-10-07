#!/usr/bin/env python3
"""CLI pública mínima del producto."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from src.data_pipeline import download_workbook, inspect_workbook, load_rows, write_json
from src.marginality import marginal_seat
from scripts.integrate_2023_calculator import load_matrix
from src.coalition_reports import make_engine

def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def main():
    parser = argparse.ArgumentParser(prog="python cli.py")
    sub = parser.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("download", help="Descarga el dataset oficial del Congreso")
    d.add_argument("--output", default="data/raw/Elecciones-Congreso.xlsx")
    i = sub.add_parser("inspect", help="Muestra hojas y cabeceras")
    i.add_argument("file", default="data/raw/Elecciones-Congreso.xlsx", nargs="?")
    n = sub.add_parser("normalize", help="Normaliza filas provinciales/candidatura")
    n.add_argument("file", default="data/raw/Elecciones-Congreso.xlsx", nargs="?")
    n.add_argument("--output", default="data/processed/congress_rows.json")

    c = sub.add_parser("coalition", help="Compara una coalición sobre la matriz 2023 real")
    c.add_argument("--parties", nargs="+", required=True)
    c.add_argument("--canonical", default="artifacts/data/election_2023_canonical.json")
    c.add_argument("--output", default=None)

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
        matrix = load_matrix(Path(args.canonical))
        engine, scenario, observed = make_engine(matrix)
        missing = [p for p in args.parties if p not in observed]
        if missing:
            raise SystemExit("BLOCKED: candidaturas no separables en la matriz 2023: " + ", ".join(missing))
        result = engine.analyze_coalition(tuple(args.parties), [scenario])
        lines = [
            "COALICIÓN — comparación 2023", "",
            f"Partidos: {' + '.join(args.parties)}",
            f"Separados: {result['separate_seats']} escaños",
            f"Coaligados: {result['coalition_seats']} escaños",
            f"Delta: {result['benefit']:+d} escaños", "",
            "Provincias decisivas:",
        ]
        if result["decisive_constituencies"]:
            lines.extend(
                f"  - {x['constituency']}: {x['separate']} → {x['coalition']} ({x['delta']:+d})"
                for x in result["decisive_constituencies"]
            )
        else:
            lines.append("  - Ninguna")
        lines += [
            "", "Fuente: matriz 2023 SECONDARY_REPLICA_VERIFIED.",
            "No se inventan votos ni se descomponen candidaturas conjuntas.",
        ]
        text = "\n".join(lines) + "\n"
        if args.output:
            Path(args.output).parent.mkdir(parents=True, exist_ok=True)
            Path(args.output).write_text(text, encoding="utf-8")
        print(text, end="")
    elif args.cmd == "marginal":
        d = _load(args.input)
        out = {}
        for c, x in d["constituencies"].items():
            out[c] = marginal_seat(x["votes"], x["seats"], x.get("blank_votes", 0), x.get("special", ""))
        print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
