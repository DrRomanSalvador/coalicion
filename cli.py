#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
from src.data_pipeline import download_workbook, inspect_workbook, load_rows, write_json

def main():
    parser = argparse.ArgumentParser(prog="coalicion")
    sub = parser.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("download", help="Descarga el dataset oficial del Congreso")
    d.add_argument("--output", default="data/raw/Elecciones-Congreso.xlsx")

    i = sub.add_parser("inspect", help="Muestra las hojas y cabeceras del dataset")
    i.add_argument("file", default="data/raw/Elecciones-Congreso.xlsx", nargs="?")

    n = sub.add_parser("normalize", help="Convierte filas provinciales/candidatura a JSON canónico")
    n.add_argument("file", default="data/raw/Elecciones-Congreso.xlsx", nargs="?")
    n.add_argument("--output", default="data/processed/congress_rows.json")

    args = parser.parse_args()
    if args.cmd == "download":
        print(download_workbook(args.output))
    elif args.cmd == "inspect":
        print(json.dumps(inspect_workbook(args.file), ensure_ascii=False, indent=2))
    elif args.cmd == "normalize":
        print(write_json(load_rows(args.file), args.output))

if __name__ == "__main__":
    main()
