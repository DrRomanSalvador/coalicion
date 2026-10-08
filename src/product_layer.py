"""Capa de producto político sobre los motores electorales existentes.

Regla: esta capa NO recalcula D'Hondt, umbrales, coaliciones ni shocks.
Adapta resultados existentes a decisiones de producto y bloquea cuando
faltan datos o una métrica no está soportada por el motor.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence

from .coalition import CoalitionDecisionEngine, CoalitionScenario
from .decision import (
    Scenario,
    apply_absolute_shift,
    coalition_result,
    sha256_json,
    validate_scenario,
)
from .electoral import allocate
from .reproducibility_contract import verify_contract
from .projection_suite import project as project_projection, compare_projections, uncertainty_summary, backtest_rows
from .rapid_decision_center import decision_snapshot


PRODUCT_VERSION = "1.0"
SUPPORTED_FUNCTIONS = (
    "decide",
    "ranking",
    "alert",
    "shock",
    "report",
    "scenarios",
    "value",
    "audit",
    "projection",
    "uncertainty",
    "backtest",
    "decision_center",
)


def _status(ok: bool, blockers: list[str] | None = None) -> dict:
    return {
        "status": "OK" if ok else "BLOCKED",
        "blockers": list(blockers or []),
    }


def _require_central(scenarios: Sequence[CoalitionScenario]) -> None:
    if not any(s.name == "central" for s in scenarios):
        raise ValueError("BLOCKED:FALTA_ESCENARIO_CENTRAL")


def _risk_text(level: str) -> str:
    return {"LOW": "BAJO", "MEDIUM": "MEDIO", "HIGH": "ALTO"}.get(level, level)


def _robustness_text(level: str) -> str:
    return {"HIGH": "ALTA", "MEDIUM": "MEDIA", "LOW": "BAJA"}.get(level, level)


def _territorial_split(items: Sequence[Mapping]) -> tuple[list[dict], list[dict]]:
    gains, losses = [], []
    for item in items:
        (gains if item["delta"] > 0 else losses).append(dict(item))
    return gains, losses


def _product_envelope(function: str, inputs: dict, result: dict,
                      assumptions: Sequence[str] = ()) -> dict:
    clean = dict(result)
    engine_result = clean.pop("_engine_result", None)
    input_hash = clean.pop("_input_hash", None)
    stable = {
        "version": PRODUCT_VERSION,
        "function": function,
        "inputs": inputs,
        "decision": clean,
        "assumptions": list(assumptions),
    }
    return {
        "product": {
            **stable,
            "status": "OK",
            "decision": clean,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "technical": {
            "engine_result": engine_result,
            "input_hash": input_hash,
            "output_hash": sha256_json(stable),
        },
    }

def decide_coalition(
    party_a: str,
    party_b: str,
    scenarios: Sequence[CoalitionScenario],
    seats_by_constituency: Mapping[str, int],
    blank_votes_by_constituency: Mapping[str, int] | None = None,
    special_by_constituency: Mapping[str, str] | None = None,
) -> dict:
    """Decisión binaria basada exclusivamente en el resultado calculado."""
    _require_central(scenarios)
    engine = CoalitionDecisionEngine(
        seats_by_constituency,
        blank_votes_by_constituency,
        special_by_constituency,
    )
    result = engine.analyze_coalition((party_a, party_b), scenarios)
    central = next(s for s in result["scenarios"] if s["name"] == "central")
    gains, losses = _territorial_split(result["decisive_constituencies"])
    decision = {
        "coalition": result["coalition"],
        "reference_scenario": "central",
        "separate_seats": central["separate_seats"],
        "coalition_seats": central["coalition_seats"],
        "seat_delta": central["delta"],
        "decision_rule": "CENTRAL_DELTA_POSITIVE" if result["benefit"] > 0 else "CENTRAL_DELTA_NON_POSITIVE",
        "decisive_constituencies": result["decisive_constituencies"],
        "beneficial_constituencies": gains,
        "harmful_constituencies": losses,
        "votes_recovered": result["price"]["threshold_votes_recovered"],
        "risk": {
            "level": _risk_text(result["risk"]["level"]),
            "weighted_non_improvement": result["risk"]["weighted_non_improvement"],
        },
        "robustness": {
            "level": _robustness_text(result["robustness"]["level"]),
            "weighted_mean_delta": result["robustness"]["weighted_mean_delta"],
            "worst_case_delta": result["robustness"]["worst_case_delta"],
            "best_case_delta": result["robustness"]["best_case_delta"],
        },
        "_engine_result": result,
    }
    return _product_envelope(
        "decide",
        {"party_a": party_a, "party_b": party_b},
        decision,
        ("Los pesos de escenarios son relativos; no se presentan como probabilidades calibradas.",
         "La decisión SÍ/NO refleja únicamente si el delta del escenario central es positivo."),
    )


def rank_coalitions(
    parties: Sequence[str],
    scenarios: Sequence[CoalitionScenario],
    seats_by_constituency: Mapping[str, int],
    blank_votes_by_constituency: Mapping[str, int] | None = None,
    special_by_constituency: Mapping[str, str] | None = None,
    min_size: int = 2,
    max_size: int | None = None,
    max_combinations: int = 100000,
) -> dict:
    """Ranking del motor existente, sin introducir un criterio nuevo."""
    _require_central(scenarios)
    engine = CoalitionDecisionEngine(
        seats_by_constituency,
        blank_votes_by_constituency,
        special_by_constituency,
    )
    result = engine.analyze_all_coalitions(
        parties, scenarios, min_size, max_size, max_combinations
    )
    # Presentación exhaustiva determinista, no recomendación.
    ranking = []
    for position, item in enumerate(result["all_coalitions"], 1):
        robustness = item["robustness"]
        risk = item["risk"]
        ranking.append({
            "position": position,
            "coalition": item["coalition"],
            "separate_seats": item["separate_seats"],
            "coalition_seats": item["coalition_seats"],
            "seat_delta": item["benefit"],
            "risk": _risk_text(risk["level"]),
            "weighted_mean_delta": robustness["weighted_mean_delta"],
            "worst_case_delta": robustness["worst_case_delta"],
        })
    return _product_envelope(
        "ranking",
        {"parties": list(parties), "min_size": min_size, "max_size": max_size},
        {
            "ranking": ranking,
            "top_by_engine_criteria": ranking[0] if ranking else None,
            "coalitions": result["all_coalitions"],
            "_engine_result": result,
        },
        ("El ranking conserva el criterio de ordenación del motor existente.",),
    )


def coalition_alert(
    party_a: str,
    party_b: str,
    scenarios: Sequence[CoalitionScenario],
    seats_by_constituency: Mapping[str, int],
    blank_votes_by_constituency: Mapping[str, int] | None = None,
    special_by_constituency: Mapping[str, str] | None = None,
) -> dict:
    """Alerta territorial: únicamente cambios de escaños calculados."""
    result = decide_coalition(
        party_a, party_b, scenarios, seats_by_constituency,
        blank_votes_by_constituency, special_by_constituency,
    )
    decision = result["product"]["decision"]
    return {
        "product": {
            "version": PRODUCT_VERSION,
            "function": "alert",
            "status": "OK",
            "decision": {
                "gains": decision["beneficial_constituencies"],
                "losses": decision["harmful_constituencies"],
                "net_seat_delta": decision["seat_delta"],
            },
            "assumptions": result["product"]["assumptions"],
        },
        "technical": result["technical"],
    }


def shock_scenario(
    input_votes: Mapping[str, Mapping[str, int]],
    seats_by_constituency: Mapping[str, int],
    party: str,
    shift: float,
    distribution: str = "uniform_by_province",
    blank_votes_by_constituency: Mapping[str, int] | None = None,
    special_by_constituency: Mapping[str, str] | None = None,
) -> dict:
    """Shock explícito; reutiliza apply_absolute_shift y allocate."""
    scenario = Scenario(
        "national_shift", party, "absolute_points", shift, distribution,
        ("no turnout change", "no vote transfer"), "user_defined", "none"
    )
    validate_scenario(scenario)
    before, after = {}, {}
    blank = blank_votes_by_constituency or {}
    special = special_by_constituency or {}
    shifted = apply_absolute_shift(input_votes, party, shift, distribution)
    for c, row in input_votes.items():
        a = allocate(row, seats_by_constituency[c],
                     sum(row.values()) + blank.get(c, 0),
                     special.get(c, ""), blank.get(c, 0))
        if a.status != "OK":
            raise RuntimeError(f"BLOCKED:{c}:{a.status}")
        before[c] = a.seats
    for c, row in shifted.items():
        a = allocate(row, seats_by_constituency[c],
                     sum(row.values()) + blank.get(c, 0),
                     special.get(c, ""), blank.get(c, 0))
        if a.status != "OK":
            raise RuntimeError(f"BLOCKED:{c}:{a.status}")
        after[c] = a.seats

    def national(matrix):
        out = {}
        for row in matrix.values():
            for p, seats in row.items():
                out[p] = out.get(p, 0) + seats
        return out

    before_n, after_n = national(before), national(after)
    parties = sorted(set(before_n) | set(after_n))
    changes = {p: after_n.get(p, 0) - before_n.get(p, 0) for p in parties}
    return _product_envelope(
        "shock",
        {"party": party, "shift": shift, "distribution": distribution},
        {
            "scenario": asdict(scenario),
            "before": {"national_seats": before_n, "by_constituency": before},
            "after": {"national_seats": after_n, "by_constituency": after},
            "seat_change": changes,
            "input_hash": sha256_json(input_votes),
            "output_hash": sha256_json(after),
            "_engine_result": {"votes": shifted, "seats": after},
            "_input_hash": sha256_json(input_votes),
        },
        tuple(scenario.assumptions),
    )


def compare_scenarios(
    party_a: str,
    party_b: str,
    scenarios: Sequence[CoalitionScenario],
    seats_by_constituency: Mapping[str, int],
    blank_votes_by_constituency: Mapping[str, int] | None = None,
    special_by_constituency: Mapping[str, str] | None = None,
) -> dict:
    result = decide_coalition(
        party_a, party_b, scenarios, seats_by_constituency,
        blank_votes_by_constituency, special_by_constituency,
    )
    engine_result = result["technical"]["engine_result"]
    outcomes = engine_result["scenarios"]
    deltas = [o["delta"] for o in outcomes]
    return _product_envelope(
        "scenarios",
        {"party_a": party_a, "party_b": party_b},
        {
            "scenarios": outcomes,
            "mean_delta": engine_result["robustness"]["weighted_mean_delta"],
            "standard_deviation": engine_result["robustness"]["weighted_std_delta"],
            "worst_case": min(deltas),
            "best_case": max(deltas),
            "weighted_favorable_share": engine_result["robustness"]["weighted_improvement"],
            "robustness": _robustness_text(engine_result["robustness"]["level"]),
            "_engine_result": engine_result,
        },
    )


def analyze_value(
    party_a: str,
    party_b: str,
    scenarios: Sequence[CoalitionScenario],
    seats_by_constituency: Mapping[str, int],
    blank_votes_by_constituency: Mapping[str, int] | None = None,
    special_by_constituency: Mapping[str, str] | None = None,
) -> dict:
    """Valor electoral medible. No inventa costes de listas no presentes en datos."""
    result = decide_coalition(
        party_a, party_b, scenarios, seats_by_constituency,
        blank_votes_by_constituency, special_by_constituency,
    )
    d = result["product"]["decision"]
    return {
        "product": {
            "version": PRODUCT_VERSION,
            "function": "value",
            "status": "OK",
            "decision": {
                "seat_benefit": d["seat_delta"],
                "votes_recovered": d["votes_recovered"],
                "threshold_wasted_votes_separate":
                    result["technical"]["engine_result"]["price"]["threshold_wasted_votes_separate"],
                "threshold_wasted_votes_coalition":
                    result["technical"]["engine_result"]["price"]["threshold_wasted_votes_coalition"],
                "measurable_value": "seat_gain_and_threshold_recovery",
                "unavailable_without_explicit_data": [
                    "list_position_cost",
                    "candidate_allocation_cost",
                    "political_autonomy_cost",
                ],
            },
            "assumptions": [
                "No se monetiza ni inventa un coste político.",
                "No se infiere reparto de listas sin datos explícitos.",
            ],
        },
        "technical": result["technical"],
    }


def generate_leader_report(
    leader: str,
    party_a: str,
    party_b: str,
    scenarios: Sequence[CoalitionScenario],
    seats_by_constituency: Mapping[str, int],
    blank_votes_by_constituency: Mapping[str, int] | None = None,
    special_by_constituency: Mapping[str, str] | None = None,
) -> dict:
    decision = decide_coalition(
        party_a, party_b, scenarios, seats_by_constituency,
        blank_votes_by_constituency, special_by_constituency,
    )
    d = decision["product"]["decision"]
    lines = [
        f"# INFORME EJECUTIVO — {leader}",
        "",
        f"## {party_a} + {party_b}",
        "",
        f"**Resultado bajo el criterio electoral calculado:** {d['decision_rule']}",
        "",
        f"- Escaños separados: {d['separate_seats']}",
        f"- Escaños coaligados: {d['coalition_seats']}",
        f"- Diferencia: {d['seat_delta']:+d}",
        f"- Votos recuperados por umbral: {d['votes_recovered']}",
        f"- Riesgo de no mejora: {d['risk']['weighted_non_improvement']:.1%}",
        f"- Robustez: {d['robustness']['level']}",
        "",
        "## Circunscripciones decisivas",
    ]
    for item in d["decisive_constituencies"]:
        lines.append(
            f"- {item['constituency']}: {item['delta']:+d} "
            f"({item['separate']} → {item['coalition']})"
        )
    lines += [
        "",
        "## Límites",
        "- No se infieren costes de listas, candidatos ni negociación política.",
        "- Los pesos de escenarios no se interpretan como probabilidades calibradas.",
    ]
    return {
        "product": {
            "version": PRODUCT_VERSION,
            "function": "report",
            "status": "OK",
            "markdown": "\\n".join(lines),
        },
        "technical": decision["technical"],
    }


def audit_decision() -> dict:
    """Auditoría contractual existente; no duplica verificación de hashes."""
    contract = verify_contract(Path("."))
    return {
        "product": {
            "version": PRODUCT_VERSION,
            "function": "audit",
            "status": "OK" if contract["status"] == "PASS" else "BLOCKED",
            "reproducibility": contract["status"],
            "traceability": "COMPLETE" if contract["status"] == "PASS" else "BLOCKED",
            "blockers": [contract["anchor"].get("reason")]
            if contract["status"] != "PASS" else [],
        },
        "technical": contract,
    }


def project(votes_by_constituency, seats_by_constituency, blank_votes_by_constituency,
            share_changes=None, turnout_factors=None, special_by_constituency=None):
    return project_projection(votes_by_constituency, seats_by_constituency, blank_votes_by_constituency,
                              share_changes, turnout_factors, special_by_constituency)


def compare_projection_results(reference, candidate):
    return compare_projections(reference, candidate)


def uncertainty(draw_results):
    return uncertainty_summary(draw_results)


def backtest(predictions, actuals):
    return backtest_rows(predictions, actuals)


def decision_center(*args, **kwargs):
    """Centro operativo único: voto → territorio → escaños → marginalidad → pactos."""
    return decision_snapshot(*args, **kwargs)
