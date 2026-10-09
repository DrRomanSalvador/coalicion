#!/usr/bin/env python3
"""Auditable marginal-seat and coalition decision analysis for the 2023 demo."""
from __future__ import annotations
import argparse, hashlib, json, sys
from fractions import Fraction
from pathlib import Path
from typing import Any
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from scripts.demo_multiparty import DEFAULT_DATA, DEFAULT_SCENARIOS, DemoError, git_blob_sha, load_dataset, read_json
from src.electoral import allocate

DEFAULT_JSON = ROOT / "artifacts/demo_decision_analysis_2023.json"
DEFAULT_REPORT = ROOT / "reports/demo_decision_analysis_2023.md"

def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def allocate_checked(votes: dict[str, int], seats: int, blank: int) -> dict[str, int]:
    result = allocate(votes, seats, sum(votes.values()) + blank, blank_votes=blank)
    if result.status != "OK": raise DemoError(f"Asignación bloqueada: {result.status}")
    if sum(result.seats.values()) != seats: raise DemoError("Los escaños no suman la magnitud.")
    return result.seats

def quotient_boundary(votes: dict[str, int], seats: dict[str, int], party: str) -> dict[str, Any]:
    count = seats.get(party, 0)
    if count < 1: return {"party": party, "status": "NO_SEAT_TO_EXPLAIN"}
    own = Fraction(votes.get(party, 0), count)
    rivals = [(Fraction(v, seats.get(other, 0)+1), other, v, seats.get(other, 0)+1)
              for other, v in votes.items() if other != party]
    if not rivals: return {"party": party, "own_last_seat_quotient": str(own)}
    rq, rival, rv, divisor = max(rivals, key=lambda x: (x[0], x[2], x[1]))
    return {"party": party, "own_last_seat_quotient": str(own),
            "own_quotient_exact": {"numerator": own.numerator, "denominator": own.denominator},
            "strongest_rival": rival, "strongest_rival_next_quotient": str(rq),
            "rival_quotient_exact": {"numerator": rq.numerator, "denominator": rq.denominator},
            "rival_votes": rv, "rival_divisor": divisor, "margin_exact": str(own-rq)}

def seats_after_extra(votes: dict[str, int], seats: int, blank: int, party: str, extra: int) -> int:
    changed = dict(votes); changed[party] = changed.get(party, 0) + extra
    result = allocate(changed, seats, sum(changed.values()) + blank, blank_votes=blank)
    if result.status == "EMPATE_ABSOLUTO_PENDIENTE": return -1
    if result.status != "OK": raise DemoError(f"Frontera bloqueada: {result.status}")
    return result.seats.get(party, 0)

def viability_frontier(votes: dict[str, int], seats: int, blank: int, party: str) -> dict[str, Any]:
    baseline = allocate_checked(votes, seats, blank); current = baseline.get(party, 0); target = current + 1
    hi = 1
    while hi <= 100_000_000 and seats_after_extra(votes, seats, blank, party, hi) < target: hi *= 2
    if hi > 100_000_000: raise DemoError(f"No se pudo acotar la frontera de {party}.")
    lo = 0
    while lo < hi:
        mid = (lo+hi)//2
        if seats_after_extra(votes, seats, blank, party, mid) >= target: hi = mid
        else: lo = mid+1
    extra = lo
    if extra and seats_after_extra(votes, seats, blank, party, extra-1) >= target:
        raise DemoError("La frontera no es mínima.")
    changed = dict(votes); changed[party] = changed.get(party, 0)+extra
    final = allocate_checked(changed, seats, blank)
    return {"candidacy": party, "current_votes": votes.get(party, 0), "current_seats": current,
            "target_seats": target, "additional_votes_minimum": extra,
            "votes_after_change": changed[party], "fixed_rival_votes": True,
            "valid_vote_total_increases_by": extra,
            "seat_allocation_after_change": {p:n for p,n in final.items() if n},
            "interpretation": "Umbral matemático con votos rivales fijos; no es predicción ni probabilidad."}

def build_analysis(data_path: Path = DEFAULT_DATA, config_path: Path = DEFAULT_SCENARIOS) -> tuple[dict, str]:
    dataset, constituencies, data_raw = load_dataset(data_path)
    config, config_raw = read_json(config_path)
    if not isinstance(config, dict) or config.get("schema") != "COALICION_MULTIPARTY_DEMO_V1":
        raise DemoError("Configuración de escenarios desconocida.")
    if config.get("election") != 2023 or config.get("regions") != ["Madrid", "Barcelona"]:
        raise DemoError("Configuración incompatible.")
    scenarios = config.get("scenarios")
    if not isinstance(scenarios, list) or [s.get("id") for s in scenarios] != ["fragmentado", "izquierda_sin_psoe", "bloque_amplio_con_psoe_psc"]:
        raise DemoError("Se requieren exactamente los tres escenarios existentes.")
    out: dict[str, Any] = {
        "schema": "COALICION_DECISION_ANALYSIS_V1", "product": "COALICIÓN", "election": 2023,
        "interpretation": "Contrafactual mecánico con votos observados; no modela transferencias, participación ni conducta electoral.",
        "official_certification": "NOT_INDEPENDENTLY_CERTIFIED",
        "method": {"allocation": "src.electoral.allocate; D’Hondt y umbral legal existente",
                   "quotients": "Fraction; comparación exacta", "coalition_effect": "agregar votos y recalcular escaños",
                   "frontier": "mínimo entero de votos adicionales; votos rivales fijos; total válido actualizado"},
        "provenance": {"provider": dataset["source"]["provider"], "source_url": dataset["source"]["url"],
                       "source_workbook_sha256": dataset["source"]["sha256"],
                       "canonical_dataset_git_blob_sha1": git_blob_sha(data_raw),
                       "scenario_config_sha256": sha256(config_raw)},
        "decision_log": [], "regions": {}}
    for region in ("Madrid", "Barcelona"):
        item = constituencies[region]; votes = item["parties"]; magnitude = item["seats"]; blank = item["blank_votes"]
        base = allocate_checked(votes, magnitude, blank)
        if {p:n for p,n in base.items() if n} != item["observed_seats"]:
            raise DemoError(f"{region}: el reparto base no reproduce el observado.")
        region_out = {"magnitude": magnitude, "valid_votes": item["valid_votes"], "blank_votes": blank,
                      "observed_seats": item["observed_seats"], "scenarios": {}, "viability_frontier": []}
        for p in sorted(votes):
            region_out["viability_frontier"].append(viability_frontier(votes, magnitude, blank, p))
        for scenario in scenarios:
            groups = scenario.get("groups", {}).get(region, {})
            lists = dict(votes)
            assigned = set()
            for label, members in groups.items():
                if not isinstance(members, list) or len(members)<2 or len(set(members)) != len(members):
                    raise DemoError(f"{scenario['id']}/{region}: grupo inválido.")
                if any(p not in votes for p in members) or assigned.intersection(members):
                    raise DemoError(f"{scenario['id']}/{region}: candidatura ausente o duplicada.")
                assigned.update(members)
                lists[label] = sum(votes[p] for p in members)
                for p in members: del lists[p]
            if sum(lists.values()) != sum(votes.values()): raise DemoError("La agrupación alteró los votos.")
            allocation = allocate_checked(lists, magnitude, blank)
            region_out["scenarios"][scenario["id"]] = {
                "assumption": scenario["assumption"], "votes_by_list": {p:v for p,v in lists.items() if v},
                "simulated_seats": {p:n for p,n in allocation.items() if n},
                "seat_delta_vs_observed": {p: allocation.get(p,0)-base.get(p,0)
                    for p in sorted(set(base)|set(allocation)) if allocation.get(p,0)!=base.get(p,0)},
                "marginal_seat_changes": [
                    {"candidacy":p, "observed_seats":base.get(p,0), "simulated_seats":allocation.get(p,0),
                     "delta":allocation.get(p,0)-base.get(p,0),
                     "quotient_explanation":(quotient_boundary(lists, allocation, p) if p in lists and allocation.get(p,0)>base.get(p,0)
                         else quotient_boundary(votes, base, p) if p in votes and base.get(p,0)>allocation.get(p,0)
                         else {"status":"LIST_ABSORBED_IN_GROUP" if p in votes and p not in lists else "NO_SEAT_CHANGE"})}
                    for p in sorted(set(base)|set(allocation)) if allocation.get(p,0)!=base.get(p,0)]}
            for label, members in groups.items():
                coalition_votes = dict(votes); coalition_votes[label] = sum(votes[p] for p in members)
                for p in members: del coalition_votes[p]
                joined = allocate_checked(coalition_votes, magnitude, blank)
                separate_count = sum(base.get(p,0) for p in members); joined_count = joined.get(label,0)
                if joined_count > separate_count: quotient = quotient_boundary(coalition_votes, joined, label)
                elif joined_count < separate_count:
                    seats_with = [(Fraction(votes[p], base[p]), p) for p in members if base.get(p,0)>0]
                    quotient = ({"party": min(seats_with)[1], "own_last_seat_quotient": str(min(seats_with)[0]),
                                 "note": "Cociente marginal de un escaño en el reparto separado."}
                                if seats_with else {"status":"NO_MEMBER_SEAT_TO_EXPLAIN"})
                else: quotient = {"status":"NO_SEAT_CHANGE"}
                out["decision_log"].append({
                    "scenario":scenario["id"], "constituency":region, "group":label, "members":members,
                    "votes":sum(votes[p] for p in members),
                    "separate_member_seats":{p:base.get(p,0) for p in members},
                    "coalition_seats":joined_count, "separate_group_seats":separate_count,
                    "seat_delta":joined_count-separate_count,
                    "member_seats_before_merge":{p:base.get(p,0) for p in members},
                    "scenario_seat_delta_vs_observed":region_out["scenarios"][scenario["id"]]["seat_delta_vs_observed"],
                    "marginal_quotient_explanation":quotient,
                    "causal_scope":"Efecto aritmético de agregar listas con votos observados; no identifica transferencias ni reacción electoral.",
                    "assumption":scenario["assumption"]})
        out["regions"][region] = region_out
    lines = ["# COALICIÓN — Informe ejecutivo de decisión (Congreso 2023)", "",
      "> **Alcance:** contrafactual mecánico con votos observados. No es predicción ni certificación oficial; no presupone transferencias.", "",
      "## Cambios de escaños por agrupación", "",
      "| Circunscripción | Escenario | Configuración | Separados | Agrupados | Diferencia |",
      "|---|---|---|---:|---:|---:|"]
    for e in out["decision_log"]:
        lines.append(f"| {e['constituency']} | {e['scenario']} | {e['group']} | {e['separate_group_seats']} | {e['coalition_seats']} | {e['seat_delta']:+d} |")
    lines += ["", "## Lectura y límites", "",
      "- La diferencia es el efecto de sumar los votos observados de las listas especificadas y volver a aplicar D’Hondt.",
      "- El JSON registra cambios por candidatura y el cociente marginal cuando hay cambio.",
      "- La frontera de viabilidad calcula los votos adicionales mínimos para el siguiente escaño bajo votos rivales fijos; el total válido aumenta en esa cantidad.",
      "- La agrupación de candidaturas menores es un supuesto del escenario, no una clasificación oficial.",
      "- No se infieren transferencias, participación futura, probabilidad, conducta electoral ni recomendación política.", "",
      "## Reproducibilidad", "",
      f"- Fuente: {dataset['source']['provider']} — {dataset['source']['url']}",
      f"- SHA-256 workbook declarado: `{dataset['source']['sha256']}`",
      f"- Git blob SHA-1 dataset: `{git_blob_sha(data_raw)}`",
      f"- SHA-256 configuración: `{sha256(config_raw)}`",
      "- Motor: `src.electoral.allocate`; cocientes exactos con fracciones.",
      "- Estado: `NOT_INDEPENDENTLY_CERTIFIED`."]
    return out, "\n".join(lines)+"\n"

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--scenarios", type=Path, default=DEFAULT_SCENARIOS)
    parser.add_argument("--output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    try:
        result, report = build_analysis(args.data, args.scenarios)
        for path, content in ((args.output, json.dumps(result, ensure_ascii=False, indent=2)+"\n"), (args.report, report)):
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(path.suffix+".tmp"); tmp.write_text(content, encoding="utf-8"); tmp.replace(path)
    except (DemoError, OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
        print(f"ERROR FAIL-CLOSED: {exc}", file=sys.stderr); return 2
    print(json.dumps({"json":str(args.output), "report":str(args.report), "decision_log_entries":len(result["decision_log"])}))
    return 0

if __name__ == "__main__": raise SystemExit(main())
