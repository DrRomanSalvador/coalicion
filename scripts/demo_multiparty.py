#!/usr/bin/env python3
"""COALICIÓN: demo multiparty reproducible para Madrid y Barcelona (generales 2023)."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.electoral import allocate
from src.coalition import coalition_decision

DEFAULT_DATA = ROOT / "artifacts/data/election_2023_canonical.json"
DEFAULT_SCENARIOS = ROOT / "config/demo_multiparty_2023.json"
DEFAULT_OUTPUT = ROOT / "artifacts/demo_multiparty_2023.json"
EXPECTED_SCHEMA = "ELECTION_2023_CONSTITUENCY_MATRIX_V2"
EXPECTED_ELECTION = 2023
EXPECTED_GIT_BLOB_SHA = "e6a164a7ca3294c36e44fa1adc6042474122bfbb"
REGIONS = ("Madrid", "Barcelona")


class DemoError(RuntimeError):
    """La demo aborta sin emitir resultados parciales."""


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(f"blob {len(raw)}\0".encode("ascii") + raw).hexdigest()


def read_json(path: Path) -> tuple[Any, bytes]:
    try:
        raw = path.read_bytes()
        return json.loads(raw), raw
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DemoError(f"JSON no disponible o inválido ({path}): {exc}") from exc


def load_dataset(path: Path) -> tuple[dict, dict, bytes]:
    dataset, raw = read_json(path)
    if not isinstance(dataset, dict):
        raise DemoError("El dataset debe ser un objeto JSON.")
    if dataset.get("schema") != EXPECTED_SCHEMA or dataset.get("election") != EXPECTED_ELECTION:
        raise DemoError("Esquema o elección inesperados.")
    if dataset.get("source_tier") != "OFFICIAL_PRIMARY":
        raise DemoError("La fuente no está etiquetada como primaria oficial.")
    source = dataset.get("source")
    if not isinstance(source, dict) or source.get("provider") != "Ministerio del Interior / Infoelectoral":
        raise DemoError("Procedencia oficial ausente o inesperada.")
    if source.get("hash_scope") != "workbook_bytes" or not source.get("sha256") or not source.get("url"):
        raise DemoError("Metadatos de hash/procedencia incompletos.")
    actual_blob = git_blob_sha(raw)
    if actual_blob != EXPECTED_GIT_BLOB_SHA:
        raise DemoError(f"El blob canónico no coincide: esperado={EXPECTED_GIT_BLOB_SHA}, obtenido={actual_blob}")
    regions = dataset.get("data", {}).get("constituencies")
    if not isinstance(regions, dict):
        raise DemoError("Falta data.constituencies.")
    for name in REGIONS:
        validate_constituency(name, regions.get(name))
    return dataset, regions, raw


def validate_constituency(name: str, item: Any) -> None:
    if not isinstance(item, dict):
        raise DemoError(f"Falta la circunscripción {name}.")
    seats, valid, blank = item.get("seats"), item.get("valid_votes"), item.get("blank_votes")
    parties, observed = item.get("parties"), item.get("observed_seats")
    if any(type(x) is not int or x <= 0 for x in (seats, valid)):
        raise DemoError(f"{name}: magnitud o votos válidos inválidos.")
    if type(blank) is not int or blank < 0:
        raise DemoError(f"{name}: votos en blanco inválidos o ausentes.")
    if not isinstance(parties, dict) or not parties or not isinstance(observed, dict):
        raise DemoError(f"{name}: matriz de candidaturas/reparto observado ausente.")
    for party, votes in parties.items():
        if not isinstance(party, str) or not party.strip() or type(votes) is not int or votes < 0:
            raise DemoError(f"{name}: candidatura o votos inválidos ({party!r}).")
    for party, count in observed.items():
        if party not in parties or type(count) is not int or count < 0:
            raise DemoError(f"{name}: reparto observado inválido ({party!r}).")
    if sum(parties.values()) + blank != valid:
        raise DemoError(f"{name}: candidaturas + blancos no coinciden con votos válidos.")
    if sum(observed.values()) != seats:
        raise DemoError(f"{name}: los escaños observados no suman {seats}.")
    allocation = allocate(parties, seats, valid, blank_votes=blank)
    if allocation.status != "OK":
        raise DemoError(f"{name}: el motor electoral canónico bloquea el reparto: {allocation.status}")
    expected = {p: n for p, n in allocation.seats.items() if n}
    if expected != observed:
        raise DemoError(f"{name}: el motor canónico no reproduce los escaños observados de 2023.")


def build_lists(parties: dict[str, int], groups: dict[str, list[str]]) -> dict[str, int]:
    """Agrupa votos de candidaturas reales sin duplicarlos ni inventar transferencias."""
    result: dict[str, int] = {}
    assigned: set[str] = set()
    for label, members in groups.items():
        if not isinstance(label, str) or not label.strip() or not isinstance(members, list) or len(members) < 2:
            raise DemoError(f"Grupo inválido: {label!r}.")
        total = 0
        for party in members:
            if party not in parties:
                raise DemoError(f"Candidatura no encontrada en el dataset: {party}")
            if party in assigned:
                raise DemoError(f"Candidatura asignada más de una vez: {party}")
            assigned.add(party)
            total += parties[party]
        result[label] = total
    for party, votes in parties.items():
        if party not in assigned:
            result[party] = votes
    if sum(result.values()) != sum(parties.values()):
        raise DemoError("La agrupación ha alterado el total de votos.")
    return dict(sorted(result.items()))


def run_demo(data_path: Path = DEFAULT_DATA, scenarios_path: Path = DEFAULT_SCENARIOS) -> dict:
    dataset, constituencies, data_raw = load_dataset(data_path)
    config, config_raw = read_json(scenarios_path)
    if not isinstance(config, dict) or config.get("schema") != "COALICION_MULTIPARTY_DEMO_V1":
        raise DemoError("Esquema de configuración de escenarios desconocido.")
    if config.get("election") != EXPECTED_ELECTION or config.get("regions") != list(REGIONS):
        raise DemoError("La configuración no coincide con las circunscripciones/año requeridos.")
    definitions = config.get("scenarios")
    required = ["fragmentado", "izquierda_sin_psoe", "bloque_amplio_con_psoe_psc"]
    if not isinstance(definitions, list) or [x.get("id") if isinstance(x, dict) else None for x in definitions] != required:
        raise DemoError("Se requieren exactamente los tres escenarios definidos, en orden.")
    results = {
        "product": "COALICIÓN",
        "election": EXPECTED_ELECTION,
        "interpretation": "Simulación mecánica contrafactual; no predice transferencias ni comportamiento electoral.",
        "official_certification": "NOT_INDEPENDENTLY_CERTIFIED",
        "source_tier": dataset["source_tier"],
        "method": "src.electoral.allocate: D’Hondt y umbral del 3%; src.coalition.coalition_decision para comparaciones de listas agrupadas.",
        "provenance": {
            "provider": dataset["source"]["provider"],
            "source_url": dataset["source"]["url"],
            "source_workbook_sha256": dataset["source"]["sha256"],
            "canonical_dataset_git_blob_sha1": git_blob_sha(data_raw),
            "scenario_config_sha256": sha256_bytes(config_raw),
        },
        "constituencies": {},
        "scenarios": [],
    }
    for region in REGIONS:
        item = constituencies[region]
        results["constituencies"][region] = {
            "seats": item["seats"],
            "valid_votes": item["valid_votes"],
            "blank_votes": item["blank_votes"],
            "observed_seats": item["observed_seats"],
        }
    # Construye el resultado completo antes de imprimir nada: no hay salida parcial.
    for scenario in definitions:
        regional = {}
        for region in REGIONS:
            item = constituencies[region]
            groups = scenario.get("groups", {}).get(region, {})
            if not isinstance(groups, dict):
                raise DemoError(f"{scenario['id']}/{region}: grupos inválidos.")
            lists = build_lists(item["parties"], groups)
            allocation = allocate(lists, item["seats"], item["valid_votes"], blank_votes=item["blank_votes"])
            if allocation.status != "OK":
                raise DemoError(f"{scenario['id']}/{region}: asignación bloqueada: {allocation.status}")
            seats = {p: n for p, n in allocation.seats.items() if n}
            comparison = []
            for members in groups.values():
                report = coalition_decision(
                    {region: item["parties"]},
                    {region: item["seats"]},
                    {region: item["blank_votes"]},
                    members,
                )
                comparison.append({
                    "members": members,
                    "separate_seats": report["separate_seats"],
                    "coalition_seats": report["coalition_seats"],
                    "delta": report["benefit"],
                })
            if scenario["id"] == "fragmentado" and seats != item["observed_seats"]:
                raise DemoError(f"{region}: escenario fragmentado no reproduce los escaños observados.")
            regional[region] = {
                "votes_by_list": lists,
                "simulated_seats": seats,
                "seat_total": sum(seats.values()),
                "coalition_comparisons": comparison,
            }
        results["scenarios"].append({
            "id": scenario["id"],
            "label": scenario["label"],
            "assumption": scenario["assumption"],
            "regions": regional,
        })
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--scenarios", type=Path, default=DEFAULT_SCENARIOS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Ruta del JSON de resultados")
    args = parser.parse_args()
    try:
        result = run_demo(args.data, args.scenarios)
    except (DemoError, ValueError, RuntimeError, KeyError, TypeError) as exc:
        print(f"ERROR FAIL-CLOSED: {exc}", file=sys.stderr)
        return 2
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\\n"
    try:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_suffix(args.output.suffix + ".tmp")
        temporary.write_text(serialized, encoding="utf-8")
        temporary.replace(args.output)
    except OSError as exc:
        print(f"ERROR: no se pudo persistir el resultado: {exc}", file=sys.stderr)
        return 2
    print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
