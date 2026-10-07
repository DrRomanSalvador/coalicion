"""Informes legibles de coaliciones sobre la matriz 2023 observada.

La identidad electoral se normaliza únicamente mediante alias cerrados y
explícitos. Nunca se descompone una candidatura conjunta en sus componentes.
"""
from __future__ import annotations
from itertools import combinations
from typing import Mapping, Sequence
from .coalition_decision_engine import CoalitionDecisionEngine, CoalitionScenario

REQUESTED_IDENTITIES = (
    "PSOE", "PP", "SUMAR", "VOX", "IU", "Podemos", "Más País",
    "Compromís", "BNG", "ERC", "JUNTS", "EAJ-PNV", "EH Bildu",
)
OBSERVABLE_IDENTITIES = (
    "PSOE", "PP", "SUMAR", "VOX", "ERC", "JUNTS", "EH Bildu",
    "EAJ-PNV", "BNG", "CCa", "CUP", "UPN", "PACMA",
)
DEFAULT_REPORT_IDENTITIES = REQUESTED_IDENTITIES + ("CCa", "CUP", "UPN", "PACMA")
IDENTITY_RULES = (
    ("PP", ("PP ",)),
    ("PSOE", ("PSOE ", "PSC ", "PSdeG-PSOE ", "PSE-EE (PSOE)",
              "PSIB-PSOE ", "PSN-PSOE ")),
    ("SUMAR", ("SUMAR ", "ECP SUMAR ",
                "MÉS PER MALLORCA-MÉS PER MENORCA-SUMAR ")),
    ("VOX", ("VOX ",)), ("ERC", ("ERC ",)), ("JUNTS", ("JUNTS ",)),
    ("EH Bildu", ("EH Bildu ",)), ("EAJ-PNV", ("EAJ-PNV ",)),
    ("BNG", ("B.N.G. ",)), ("CCa", ("CCa ",)),
    ("CUP", ("CUP-PR ",)), ("UPN", ("U.P.N. ",)), ("PACMA", ("PACMA ",)),
)

def party_identity(raw_name: str) -> str | None:
    matches = [i for i, prefixes in IDENTITY_RULES
               if any(raw_name.startswith(p) for p in prefixes)]
    if len(matches) > 1:
        raise ValueError(f"AMBIGUOUS_PARTY_ALIAS:{raw_name}:{matches}")
    return matches[0] if matches else None

def aggregate_identities(raw_constituencies: Mapping[str, Mapping[str, int]]):
    out = {}
    for constituency, row in raw_constituencies.items():
        merged = {}
        for raw_name, votes in row.items():
            identity = party_identity(raw_name)
            key = identity or raw_name
            merged[key] = merged.get(key, 0) + votes
        out[constituency] = merged
    return out

def build_scenario(matrix: Mapping):
    constituencies = matrix["data"]["constituencies"]
    votes = aggregate_identities({n: c["parties"] for n, c in constituencies.items()})
    seats = {n: c["seats"] for n, c in constituencies.items()}
    blanks = {n: c["blank_votes"] for n, c in constituencies.items()}
    special = {n: c.get("special", "") for n, c in constituencies.items()}
    observed = {i for i in OBSERVABLE_IDENTITIES if any(i in r for r in votes.values())}
    return votes, seats, blanks, special, sorted(observed)

def make_engine(matrix: Mapping):
    votes, seats, blanks, special, observed = build_scenario(matrix)
    engine = CoalitionDecisionEngine(seats, blanks, special)
    scenario = CoalitionScenario(
        name="central", votes=votes, weight=1.0,
        assumptions=("Votos observados en la matriz 2023; sin transferencia de votos.",),
        source="SECONDARY_REPLICA_VERIFIED",
    )
    engine._validate(scenario)
    return engine, scenario, observed

def supported_parties(matrix: Mapping, requested: Sequence[str] = DEFAULT_REPORT_IDENTITIES):
    _, _, _, _, observed = build_scenario(matrix)
    return [p for p in requested if p in observed], [p for p in requested if p not in observed]

def pairwise_report(matrix: Mapping, parties: Sequence[str] | None = None):
    engine, scenario, observed = make_engine(matrix)
    requested = list(parties or DEFAULT_REPORT_IDENTITIES)
    selected = [p for p in requested if p in observed]
    unsupported = [p for p in requested if p not in observed]
    results = []
    for a, b in combinations(selected, 2):
        r = engine.analyze_coalition((a, b), [scenario])
        results.append({
            "party_a": a, "party_b": b,
            "separate_seats": r["separate_seats"],
            "coalition_seats": r["coalition_seats"],
            "delta": r["benefit"],
            "decisive_constituencies": r["decisive_constituencies"],
            "threshold_votes_recovered": r["price"]["threshold_votes_recovered"],
        })
    results.sort(key=lambda x: (x["party_a"], x["party_b"]))
    return results, unsupported

def baseline_seats(matrix: Mapping):
    engine, scenario, _ = make_engine(matrix)
    result = {}
    for constituency, row in scenario.votes.items():
        allocation = engine._allocate(row, constituency)
        for party, seats in allocation.seats.items():
            result[party] = result.get(party, 0) + seats
    return dict(sorted(result.items(), key=lambda x: (-x[1], x[0])))

def find_pair(results, a: str, b: str):
    return next((r for r in results if {r["party_a"], r["party_b"]} == {a, b}), None)

def markdown_all(results, unsupported, selected):
    lines = [
        "# Informe de coaliciones — Congreso 2023", "",
        "> Comparación matemática sobre la matriz 2023 SECONDARY_REPLICA_VERIFIED.",
        "> No es una recomendación política. La cifra compara votos observados",
        "> por circunscripción con las mismas candidaturas separadas frente a una",
        "> candidatura fusionada y vuelve a ejecutar D'Hondt.", "",
        f"**Partidos observables incluidos:** {', '.join(selected)}",
        f"**Comparaciones bilaterales:** {len(results)}", "",
        "## Partidos solicitados que no pueden calcularse", "",
    ]
    if unsupported:
        lines.extend(
            f"- **{p}**: no existe como candidatura separable en la matriz 2023; "
            "se mantiene bloqueado para evitar repartir votos de candidaturas conjuntas."
            for p in unsupported
        )
    else:
        lines.append("- Ninguno.")
    lines += [
        "", "## Comparación bilateral completa", "",
        "| Coalición | Separados | Coaligados | Delta | Provincias decisivas |",
        "|---|---:|---:|---:|---|",
    ]
    for r in results:
        decisive = ", ".join(
            f'{x["constituency"]} ({x["delta"]:+d})'
            for x in r["decisive_constituencies"]
        ) or "Ninguna"
        lines.append(
            f'| {r["party_a"]} + {r["party_b"]} | {r["separate_seats"]} | '
            f'{r["coalition_seats"]} | {r["delta"]:+d} | {decisive} |'
        )
    lines += [
        "", "## Lectura", "",
        "- **Separados**: suma de los escaños de ambas candidaturas por separado.",
        "- **Coaligados**: suma de votos por circunscripción y nueva asignación D'Hondt.",
        "- **Delta**: coaligados menos separados.",
        "- **Provincias decisivas**: circunscripciones donde cambia el resultado.",
        "", "## Procedencia y límites", "",
        "- Fuente: réplica secundaria verificada de la matriz 2023.",
        "- La certificación oficial primaria sigue separada y pendiente.",
        "- No se inventan votos, transferencias, encuestas ni probabilidades.",
    ]
    return "\n".join(lines) + "\n"

def markdown_executive(results, unsupported):
    profiles = {
        "Yolanda Díaz": ("SUMAR", ("PSOE", "ERC", "JUNTS")),
        "Pedro Sánchez": ("PSOE", ("SUMAR", "ERC", "JUNTS")),
        "Alberto Núñez Feijóo": ("PP", ("VOX", "EAJ-PNV")),
        "Santiago Abascal": ("VOX", ("PP", "EAJ-PNV")),
    }
    lines = [
        "# Resumen ejecutivo factual — Coaliciones 2023", "",
        "> Documento neutral de resultados matemáticos. No contiene recomendaciones.", "",
    ]
    for leader, (party, partners) in profiles.items():
        lines += [f"## {leader} — {party}", ""]
        for partner in partners:
            r = find_pair(results, party, partner)
            if r:
                decisive = ", ".join(
                    f'{x["constituency"]} ({x["delta"]:+d})'
                    for x in r["decisive_constituencies"]
                ) or "ninguna"
                lines.append(
                    f"- **{party} + {partner}**: {r['separate_seats']} separados → "
                    f"{r['coalition_seats']} coaligados (**{r['delta']:+d}**); "
                    f"provincias decisivas: {decisive}."
                )
            else:
                lines.append(f"- **{party} + {partner}**: no calculable con la matriz observable.")
        lines.append("")
    if unsupported:
        lines += ["## Peticiones no observables", ""]
        lines += [f"- **{p}**: bloqueado; no hay voto separable observable en 2023."
                  for p in unsupported]
        lines.append("")
    lines += [
        "## Criterio de uso", "",
        "Estas cifras describen el efecto mecánico de fusionar candidaturas sobre los votos observados de 2023. "
        "No modelan negociación política, comportamiento futuro, transferencia de voto ni probabilidad electoral.",
    ]
    return "\n".join(lines) + "\n"
