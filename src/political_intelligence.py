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



COMPONENTS: dict[str, str] = {
    "source_registry": "config/political_intelligence_sources.json",
    "canonical_data": "artifacts/data/election_2023_canonical.json",
    "electoral_engine": "src/electoral.py",
    "prediction": "src/prediction.py",
    "oos": "src/oos_pipeline.py",
    "calibration": "src/probabilistic_calibration.py",
    "uncertainty": "src/uncertainty.py",
    "marginality": "src/marginality.py",
    "coalition": "src/coalition.py",
    "decision": "src/rapid_decision_center.py",
    "electoral_intelligence": "src/electoral_intelligence.py",
    "poll_monitor": "src/poll_monitor.py",
    "poll_analytics": "src/poll_analytics.py",
    "evidence_certificate": "src/evidence_certificate.py",
    "reproducibility": "src/reproducibility_contract.py",
    "historical_validator": "scripts/validate_historical_data.py",
    "historical_oos": "scripts/run_full_oos.py",
    "historical_calibration": "scripts/complete_historical_calibration.py",
    "seec_production": "scripts/run_seec_production.py",
    "master_certification": "scripts/master_certification.py",
    "operational_briefing": "src/operational_briefing.py",
    "telegram_bot": "src/telegram_bot.py",
    "telegram_notifier": "src/telegram_notifier.py",
    "miniapp": "web/telegram/index.html",
    "master_manifest_builder": "scripts/build_political_intelligence_master_manifest.py",
}


def _path_status(relative: str) -> dict[str, Any]:
    path = ROOT / relative
    if path.is_file():
        raw = path.read_bytes()
        return {"state": "PRESENT", "path": relative, "bytes": len(raw), "sha256": sha256(raw).hexdigest()}
    if path.is_dir():
        files = sorted(p for p in path.rglob("*") if p.is_file())
        return {
            "state": "PRESENT" if files else "EMPTY",
            "path": relative,
            "file_count": len(files),
            "bytes": sum(p.stat().st_size for p in files),
        }
    return {"state": "MISSING", "path": relative}


def component_status() -> dict[str, Any]:
    """Reporta el ensamblaje real del sistema sin ejecutar inferencia ni inventar evidencia."""
    components = {name: _path_status(path) for name, path in COMPONENTS.items()}
    return {
        "schema": "COALICION_INTELLIGENCE_COMPONENT_STATUS_V1",
        "components": components,
        "all_code_components_present": all(x["state"] == "PRESENT" for x in components.values()),
    }


def intelligence_snapshot(*, as_of: str | date) -> dict[str, Any]:
    """Contrato único de estado: fuentes → evidencia → modelos → decisión → auditoría."""
    if isinstance(as_of, str):
        as_of = date.fromisoformat(as_of)
    registry = validate_registry()
    readiness_state = readiness()
    graph = build_evidence_graph(as_of=as_of)
    components = component_status()
    gates = {
        "registry": registry["status"] == "PASS",
        "evidence_materialized": not readiness_state["blockers"],
        "code_assembly": components["all_code_components_present"],
        "fail_closed": graph["policy"]["fail_closed"],
    }
    status = "READY_FOR_EXECUTION" if all(gates.values()) else "BLOCKED"
    payload = {
        "schema": "COALICION_POLITICAL_INTELLIGENCE_SNAPSHOT_V1",
        "as_of": as_of.isoformat(),
        "status": status,
        "gates": gates,
        "registry": registry,
        "readiness": readiness_state,
        "components": components,
        "evidence_graph_hash": graph["hash"],
        "pipeline": [
            "official_sources", "ingestion", "validation", "oos", "calibration",
            "prediction", "territorialization", "seats", "uncertainty",
            "marginality", "coalition_counterfactuals", "decision_snapshot",
            "monitoring", "briefing", "telegram", "audit", "reproducibility",
        ],
        "policy": {
            "neutral": True,
            "descriptive_only": True,
            "no_persuasion": True,
            "no_microtargeting": True,
            "no_hidden_imputation": True,
            "no_certification_without_evidence": True,
        },
    }
    payload["hash"] = _hash(payload)
    return payload

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
