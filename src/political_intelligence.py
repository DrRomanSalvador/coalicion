"""Thin neutral integration layer for COALICIÓN.

Connects the source bibliography to existing canonical engines without creating
parallel electoral, prediction or coalition mathematics. It reports provenance
and evidence readiness and delegates computation to canonical modules.
"""
from __future__ import annotations

from datetime import date
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "config" / "political_intelligence_sources.json"


def _load_registry() -> dict[str, Any]:
    if not REGISTRY.exists():
        raise RuntimeError("BLOCKED: political intelligence source registry missing")
    try:
        data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError("BLOCKED: invalid political intelligence source registry") from exc
    if data.get("policy", {}).get("fail_closed") is not True:
        raise RuntimeError("BLOCKED: source registry is not fail-closed")
    return data


def _hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(raw.encode("utf-8")).hexdigest()


def source_registry() -> dict[str, Any]:
    return _load_registry()


def validate_registry() -> dict[str, Any]:
    data = _load_registry()
    elections = data["official_election_results"]["elections"]
    if len(elections) != 16:
        raise RuntimeError(f"BLOCKED: expected 16 canonical general elections through 2023, got {len(elections)}")
    if elections[-1]["id"] != "2023J" or elections[-1]["date"] != "2023-07-23":
        raise RuntimeError("BLOCKED: canonical 2023 election date is inconsistent")
    urls = [x["url"] for x in elections]
    if len(urls) != len(set(urls)):
        raise RuntimeError("BLOCKED: duplicate election source URLs")
    if data["official_candidacies_2023"]["target"] != "data/official/candidacies/OFFICIAL_2023_CANDIDACY_MATRIX.csv":
        raise RuntimeError("BLOCKED: candidacy target drift")
    return {
        "status": "PASS",
        "registry_version": data["schema"],
        "canonical_general_elections": len(elections),
        "data_materialization": "NOT_ASSERTED_BY_REGISTRY",
        "registry_hash": _hash(data),
    }


def evidence_requirements() -> dict[str, Any]:
    return {
        "official_2023_candidacy_matrix": {
            "path": "data/official/candidacies/OFFICIAL_2023_CANDIDACY_MATRIX.csv",
            "required": True,
        },
        "historical_results": {
            "path": "data/official/results/",
            "required_elections": 16,
        },
        "survey_evidence": {
            "path": "data/surveys/",
            "field_date_required_for_oos": True,
        },
        "demographics": {
            "path": "data/demographics/",
            "required_for_mrp": True,
        },
        "certification_case": {
            "path": "data/certification/",
            "required_for_certification": True,
        },
    }


def readiness(*, require_historical: bool = True, require_candidacies: bool = True) -> dict[str, Any]:
    registry = validate_registry()
    req = evidence_requirements()
    blockers: list[str] = []

    if require_candidacies and not (ROOT / req["official_2023_candidacy_matrix"]["path"]).exists():
        blockers.append("PRIMARY_2023_MATRIX_MATERIALIZATION")

    if require_historical:
        result_dir = ROOT / req["historical_results"]["path"]
        found = sorted(result_dir.glob("OFFICIAL_*_RESULTS.csv")) if result_dir.exists() else []
        if len(found) < req["historical_results"]["required_elections"]:
            blockers.append("HISTORICAL_RESULTS_MATERIALIZATION")

    if not (ROOT / req["survey_evidence"]["path"]).exists():
        blockers.append("SURVEY_EVIDENCE_MATERIALIZATION")

    return {
        "status": "BLOCKED" if blockers else "READY",
        "blockers": blockers,
        "registry": registry,
        "requirements": req,
    }


def build_evidence_graph(*, as_of: str | date) -> dict[str, Any]:
    if isinstance(as_of, str):
        as_of = date.fromisoformat(as_of)
    registry = _load_registry()
    nodes = []
    for election in registry["official_election_results"]["elections"]:
        nodes.append({
            "id": f"election:{election['id']}",
            "kind": "official_result_source",
            "date": election["date"],
            "url": election["url"],
            "usable_as_of": election["date"] <= as_of.isoformat(),
        })
    for item in registry["private_surveys"]:
        nodes.append({
            "id": f"source:{item['id']}",
            "kind": "survey_source",
            "role": item["role"],
            "url": item["url"],
        })
    official = registry["official_surveys"]
    nodes.append({
        "id": "source:cis",
        "kind": "survey_source",
        "role": official["role"],
        "url": official["url"],
    })
    nodes.append({
        "id": "law:LOREG",
        "kind": "electoral_law",
        "url": registry["legal"][0]["url"],
        "role": "PRIMARY_LEGAL",
    })
    edges = [
        {"from": "source:cis", "to": "prediction", "relation": "survey_evidence"},
        {"from": "source:myf", "to": "prediction", "relation": "survey_evidence"},
        {"from": "source:sigma_dos", "to": "prediction", "relation": "survey_evidence"},
        {"from": "source:nc_report", "to": "prediction", "relation": "survey_evidence"},
        {"from": "law:LOREG", "to": "electoral_engine", "relation": "allocation_rules"},
        {"from": "prediction", "to": "territory", "relation": "validated_prediction"},
        {"from": "territory", "to": "electoral_engine", "relation": "territorial_votes"},
        {"from": "electoral_engine", "to": "decision_snapshot", "relation": "seats"},
        {"from": "decision_snapshot", "to": "coalition_counterfactuals", "relation": "decision_input"},
    ]
    payload = {
        "schema": "COALICION_EVIDENCE_GRAPH_V1",
        "as_of": as_of.isoformat(),
        "nodes": nodes,
        "edges": edges,
        "policy": {
            "descriptive_only": True,
            "no_persuasion": True,
            "no_microtargeting": True,
            "no_hidden_imputation": True,
            "fail_closed": True,
        },
    }
    payload["hash"] = _hash(payload)
    return payload
