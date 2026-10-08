"""CLI de producto: preguntas políticas, resultados calculados y trazabilidad."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from src.product_layer import (
    decide_coalition, rank_coalitions, coalition_alert, shock_scenario,
    generate_leader_report, compare_scenarios, analyze_value, audit_decision,
)
from src.coalition import CoalitionScenario


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def scenarios_from(path):
    data = load(path)
    raw = data["scenarios"] if "scenarios" in data else [data]
    return [
        CoalitionScenario(
            name=s["name"],
            votes=s["votes"],
            weight=float(s.get("weight", 1.0)),
            assumptions=tuple(s.get("assumptions", ())),
            source=s.get("source", "input_dataset"),
        )
        for s in raw
    ]


def common_data(path):
    d = load(path)
    return d["seats"], d.get("blank", {}), d.get("special", {})


def main():
    p = argparse.ArgumentParser(prog="political_product")
    sub = p.add_subparsers(dest="cmd", required=True)

    def coal_parser(name):
        x = sub.add_parser(name)
        x.add_argument("parties", nargs="+")
        x.add_argument("--input", required=True)
        x.add_argument("--scenarios", required=True)
        return x

    for name in ("decide", "alert", "scenarios", "value"):
        coal_parser(name)

    r = sub.add_parser("ranking")
    r.add_argument("parties", nargs="+")
    r.add_argument("--input", required=True)
    r.add_argument("--scenarios", required=True)
    r.add_argument("--min-size", type=int, default=2)
    r.add_argument("--max-size", type=int)
    r.add_argument("--max-combinations", type=int, default=100000)

    s = sub.add_parser("shock")
    s.add_argument("--input", required=True)
    s.add_argument("--party", required=True)
    s.add_argument("--shift", type=float, required=True)
    s.add_argument("--distribution", choices=["uniform_by_province"], default="uniform_by_province")

    rep = sub.add_parser("report")
    rep.add_argument("--input", required=True)
    rep.add_argument("--scenarios", required=True)
    rep.add_argument("--leader", required=True)
    rep.add_argument("--party-a", required=True)
    rep.add_argument("--party-b", required=True)

    sub.add_parser("audit")
    a = p.parse_args()

    if a.cmd == "audit":
        out = audit_decision()
    elif a.cmd == "shock":
        d = load(a.input)
        out = shock_scenario(
            d["votes"], d["seats"], a.party, a.shift, a.distribution,
            d.get("blank", {}), d.get("special", {}),
        )
    else:
        ss = scenarios_from(a.scenarios)
        seats, blank, special = common_data(a.input)
        if a.cmd == "decide":
            if len(a.parties) != 2:
                p.error("decide requiere exactamente dos partidos")
            out = decide_coalition(a.parties[0], a.parties[1], ss, seats, blank, special)
        elif a.cmd == "alert":
            if len(a.parties) != 2:
                p.error("alert requiere exactamente dos partidos")
            out = coalition_alert(a.parties[0], a.parties[1], ss, seats, blank, special)
        elif a.cmd == "ranking":
            out = rank_coalitions(
                a.parties, ss, seats, blank, special,
                a.min_size, a.max_size, a.max_combinations,
            )
        elif a.cmd == "scenarios":
            if len(a.parties) != 2:
                p.error("scenarios requiere exactamente dos partidos")
            out = compare_scenarios(a.parties[0], a.parties[1], ss, seats, blank, special)
        elif a.cmd == "value":
            if len(a.parties) != 2:
                p.error("value requiere exactamente dos partidos")
            out = analyze_value(a.parties[0], a.parties[1], ss, seats, blank, special)
        elif a.cmd == "report":
            out = generate_leader_report(
                a.leader, a.party_a, a.party_b, ss, seats, blank, special
            )
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
