#!/usr/bin/env python3
"""CLI reproducible de COALICIÓN.

Mantiene los comandos de ingestión históricos y añade la interfaz operativa
documentada para 2023. Todo análisis electoral exige matriz canónica primaria
y falla cerrado si falta una magnitud esencial.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from src.data import download_workbook, inspect_workbook, load_rows, write_json
from src.decision import coalition_result, apply_absolute_shift, Scenario, validate_scenario
from src.marginality import marginal_seat
from src.political_intelligence import intelligence_snapshot
from src.electoral import allocate

CANONICAL = Path("artifacts/data/election_2023_canonical.json")


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _load_canonical(election: str):
    if election != "2023":
        raise SystemExit("BLOCKED: solo 2023 está materializado en la matriz canónica.")
    if not CANONICAL.is_file():
        raise SystemExit("BLOCKED: falta artifacts/data/election_2023_canonical.json")
    data = _load(CANONICAL)
    if data.get("source") != "INTERIOR_PRIMARY":
        raise SystemExit("BLOCKED: la matriz no procede de Interior.")
    provinces = data.get("data", {}).get("provinces", [])
    if len(provinces) != 52 or sum(p.get("seats", 0) for p in provinces) != 350:
        raise SystemExit("BLOCKED: matriz incompleta; se requieren 52 circunscripciones y 350 escaños.")
    votes, seats = {}, {}
    for p in provinces:
        votes[p["name"]] = {x["name"]: x["votes"] for x in p["parties"]}
        seats[p["name"]] = p["seats"]
    valid = data.get("data", {}).get("valid_votes")
    blank = data.get("data", {}).get("blank_votes", {})
    special = data.get("data", {}).get("special", {})
    if not isinstance(valid, dict) or set(valid) != set(votes):
        raise SystemExit("BLOCKED: faltan votos válidos oficiales por circunscripción.")
    return {"votes": votes, "seats": seats, "valid_votes": valid, "blank": blank, "special": special}


def _load_input(path):
    d = _load(path)
    if "constituencies" in d:
        return d
    if "votes" in d and "seats" in d:
        return d
    raise SystemExit("BLOCKED: input sin esquema electoral reconocido.")


def cmd_download(a):
    print(download_workbook(a.output))


def cmd_inspect(a):
    print(json.dumps(inspect_workbook(a.file), ensure_ascii=False, indent=2))


def cmd_normalize(a):
    print(write_json(load_rows(a.file), a.output))


def cmd_coalition(a):
    d = _load_canonical(a.election) if a.input is None else _load_input(a.input)
    r = coalition_result(d["votes"], d["seats"], d["valid_votes"], tuple(a.parties),
                         special=d.get("special"), blank=d.get("blank"))
    print(json.dumps(r, ensure_ascii=False, indent=2))


def cmd_scenario(a):
    d = _load_canonical(a.election) if a.input is None else _load_input(a.input)
    scenario = Scenario("national_shift", a.party, "absolute_points", a.shift,
                        a.distribution, ("no turnout change", "no vote transfer"),
                        "user_defined", "none")
    validate_scenario(scenario)
    votes = apply_absolute_shift(d["votes"], a.party, a.shift, a.distribution)
    result = {}
    for constituency, row in votes.items():
        # A national_shift changes the party vote total. Valid votes must be
        # recomputed from the scenario, never copied from the baseline.
        blank = d.get("blank", {}).get(constituency, 0)
        valid = sum(row.values()) + blank
        if valid < 0:
            raise SystemExit(f"BLOCKED: {constituency}: votos válidos negativos")
        x = allocate(row, d["seats"][constituency], valid,
                     d.get("special", {}).get(constituency, ""),
                     d.get("blank", {}).get(constituency, 0))
        if x.status != "OK":
            raise SystemExit(f"BLOCKED: {constituency}: {x.status}")
        result[constituency] = x.seats
    print(json.dumps({"scenario": scenario.__dict__, "votes": votes, "seats": result},
                     ensure_ascii=False, indent=2))


def cmd_marginal(a):
    d = _load_canonical(a.election) if a.input is None else _load_input(a.input)
    out = {}
    for constituency, votes in d["votes"].items():
        out[constituency] = marginal_seat(
            votes, d["seats"][constituency], d.get("blank", {}).get(constituency, 0),
            d.get("special", {}).get(constituency, "")
        )
    print(json.dumps(out, ensure_ascii=False, indent=2))


def cmd_intelligence(a):
    from datetime import date\n    snapshot = intelligence_snapshot(as_of=a.as_of or date.today().isoformat())
    print(json.dumps(snapshot, ensure_ascii=False, indent=2))


def cmd_audit(a):
    cert = Path(a.certificate or "artifacts/audit/certificate_2023.json")
    if not cert.is_file():
        raise SystemExit("BLOCKED: certificado inexistente")
    d = _load(cert)
    print(json.dumps({
        "certificate": str(cert),
        "election": d.get("election"),
        "source_of_truth": d.get("source_of_truth"),
        "validation_status": d.get("validation_status"),
        "province_count": d.get("province_count"),
        "merkle_root": d.get("merkle_root"),
        "certification_status": "CERTIFIED_PRIMARY_MATRIX" if d.get("validation_status") == "PASS" and d.get("province_count") == 52 else "BLOCKED"
    }, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(prog="coalicion")
    sub = parser.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("download")
    d.add_argument("--output", default="data/raw/Elecciones-Congreso.xlsx")
    d.set_defaults(fn=cmd_download)

    i = sub.add_parser("inspect")
    i.add_argument("file", nargs="?", default="data/raw/Elecciones-Congreso.xlsx")
    i.set_defaults(fn=cmd_inspect)

    n = sub.add_parser("normalize")
    n.add_argument("file", nargs="?", default="data/raw/Elecciones-Congreso.xlsx")
    n.add_argument("--output", default="data/processed/congress_rows.json")
    n.set_defaults(fn=cmd_normalize)

    c = sub.add_parser("coalition")
    c.add_argument("--parties", nargs="+", required=True)
    c.add_argument("--election", default="2023")
    c.add_argument("--input")
    c.set_defaults(fn=cmd_coalition)

    s = sub.add_parser("scenario")
    s.add_argument("--party", required=True)
    s.add_argument("--shift", type=float, required=True)
    s.add_argument("--distribution", choices=["uniform_by_province", "unspecified"], default="unspecified")
    s.add_argument("--election", default="2023")
    s.add_argument("--input")
    s.set_defaults(fn=cmd_scenario)

    m = sub.add_parser("marginal-seats")
    m.add_argument("--election", default="2023")
    m.add_argument("--input")
    m.set_defaults(fn=cmd_marginal)

    pi = sub.add_parser("intelligence-status")
    pi.add_argument("--as-of", default=None)
    pi.set_defaults(fn=cmd_intelligence)

    au = sub.add_parser("audit")
    au.add_argument("election", default="2023", nargs="?")
    au.add_argument("--certificate")
    au.set_defaults(fn=cmd_audit)

    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
