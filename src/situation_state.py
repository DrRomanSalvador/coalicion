"""Canonical situation-state contract for COALICIÓN.

This module is a presentation/orchestration layer only. It never invents
observations, converts national data into territory, or makes political
recommendations. It consumes materialized repository evidence and fails closed
when the minimum evidence contract is not satisfied.
"""
from __future__ import annotations

from datetime import date, datetime
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
OBSERVATIONS = ROOT / "artifacts/estimation/observations.json"
SOURCE_COVERAGE = ROOT / "ci_evidence/poll_source_coverage.json"
MISSION = ROOT / "config/situation_mission.json"
OUTPUT = ROOT / "artifacts/situation_state.json"
SCHEMA = "COALICION_SITUATION_STATE_V1"
VERSION = "1.0"


class SituationStateBlocked(RuntimeError):
    pass


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise SituationStateBlocked(f"BLOCKED: required evidence missing: {path.relative_to(ROOT)}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SituationStateBlocked(f"BLOCKED: invalid JSON: {path.relative_to(ROOT)}") from exc
    if not isinstance(value, dict):
        raise SituationStateBlocked(f"BLOCKED: expected object: {path.relative_to(ROOT)}")
    return value


def _hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(raw.encode("utf-8")).hexdigest()


def _mission() -> dict[str, Any]:
    if not MISSION.exists():
        return {
            "id": "situacion-electoral",
            "label": "Situación electoral",
            "focus": ["cambios", "evidencia", "territorio", "incertidumbre"],
        }
    data = _read(MISSION)
    if data.get("fail_closed") is not True:
        raise SituationStateBlocked("BLOCKED: situation mission is not fail-closed")
    return data


def _poll_changes(polls: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    dated = []
    for poll in polls:
        try:
            d = date.fromisoformat(str(poll.get("publication_date", ""))[:10])
        except ValueError:
            continue
        dated.append((d, poll))
    dated.sort(key=lambda x: (x[0], str(x[1].get("poll_id", ""))), reverse=True)
    if len(dated) < 2:
        return []
    latest_date, latest = dated[0]
    previous_date, previous = dated[1]
    latest_parties = latest.get("parties", {})
    previous_parties = previous.get("parties", {})
    if not isinstance(latest_parties, Mapping) or not isinstance(previous_parties, Mapping):
        return []
    rows = []
    for party in sorted(set(latest_parties) | set(previous_parties)):
        try:
            delta = float(latest_parties.get(party, 0)) - float(previous_parties.get(party, 0))
        except (TypeError, ValueError):
            continue
        if delta == 0:
            continue
        rows.append({
            "type": "poll_observation_change",
            "party": party,
            "delta_pp": round(delta, 3),
            "latest_poll_date": latest_date.isoformat(),
            "previous_poll_date": previous_date.isoformat(),
            "latest_poll_id": latest.get("poll_id"),
            "previous_poll_id": previous.get("poll_id"),
            "evidence": [latest.get("source_url"), previous.get("source_url")],
        })
    return sorted(rows, key=lambda x: (-abs(x["delta_pp"]), x["party"]))


def build_situation_state(*, as_of: datetime | None = None) -> dict[str, Any]:
    observations = _read(OBSERVATIONS)
    coverage = _read(SOURCE_COVERAGE)
    mission = _mission()

    if observations.get("policy", {}).get("observed_only") is not True:
        raise SituationStateBlocked("BLOCKED: observations are not observed-only")
    if observations.get("policy", {}).get("national_to_territorial_inference") is not False:
        raise SituationStateBlocked("BLOCKED: national-to-territorial inference policy drift")
    if coverage.get("fail_closed") is not True:
        raise SituationStateBlocked("BLOCKED: source coverage is not fail-closed")

    polls = [x for x in observations.get("polls", []) if isinstance(x, Mapping)]
    territorial_count = int(observations.get("territorial_poll_count", 0) or 0)
    national_count = int(observations.get("national_poll_count", 0) or 0)

    changes = _poll_changes(polls)
    if territorial_count == 0:
        changes.append({
            "type": "evidence_gap",
            "code": "NO_TERRITORIAL_OBSERVATION",
            "summary": "No hay observaciones territoriales 2026 materializadas.",
            "evidence": ["artifacts/estimation/observations.json"],
        })

    latest = max(
        (str(p.get("publication_date", "")) for p in polls if p.get("publication_date")),
        default=None,
    )
    questions = [
        {
            "id": "Q_EVIDENCE_FRESHNESS",
            "question": "¿Cuál es la evidencia electoral más reciente y qué antigüedad tiene?",
            "reason": "La frescura de la evidencia condiciona cualquier lectura actual.",
        },
        {
            "id": "Q_TERRITORY",
            "question": "¿Qué evidencia territorial explícita existe realmente?",
            "reason": "No se permite convertir porcentajes nacionales en observaciones territoriales.",
        },
        {
            "id": "Q_SOURCE_HEALTH",
            "question": "¿Qué fuentes están operativas y cuáles tienen incidencias?",
            "reason": "Una incidencia de fuente no debe convertirse silenciosamente en ausencia de evidencia.",
        },
    ]
    uncertainties = []
    if territorial_count == 0:
        uncertainties.append({
            "code": "TERRITORIAL_UNCERTAINTY",
            "statement": "No puede inferirse una situación territorial 2026 a partir de las observaciones nacionales disponibles.",
            "severity": "HIGH",
            "evidence": ["artifacts/estimation/observations.json"],
        })
    missing_field_dates = sum(
        1 for p in polls if not p.get("fieldwork_start") or not p.get("fieldwork_end")
    )
    if missing_field_dates:
        uncertainties.append({
            "code": "FIELD_DATE_MISSING",
            "statement": f"{missing_field_dates} observación(es) no contienen fechas de campo materializadas.",
            "severity": "MEDIUM",
            "evidence": ["artifacts/estimation/observations.json"],
        })

    source_status = {
        "configured": coverage.get("last_runtime_coverage", {}).get("sources_checked"),
        "primary": coverage.get("primary_sources"),
        "healthy_primary": coverage.get("healthy_primary_sources"),
        "unhealthy_primary": coverage.get("unhealthy_primary_sources"),
        "status": coverage.get("status"),
    }

    if uncertainties:
        radar = "UNCERTAINTY"
    elif changes:
        radar = "ATTENTION"
    else:
        radar = "NORMAL"

    timestamp = as_of or datetime.now(ZoneInfo("Europe/Madrid"))
    inputs = {
        "observations": observations,
        "coverage": coverage,
        "mission": mission,
    }
    state = {
        "schema": SCHEMA,
        "version": VERSION,
        "as_of": timestamp.isoformat(),
        "mission": mission,
        "radar": radar,
        "headline": {
            "changed": changes[:3],
            "questions": questions[:3],
            "uncertainties": uncertainties[:1],
        },
        "counts": {
            "national_polls": national_count,
            "territorial_polls": territorial_count,
            "latest_poll_date": latest,
        },
        "source_health": source_status,
        "evidence": {
            "observations_path": str(OBSERVATIONS.relative_to(ROOT)),
            "source_coverage_path": str(SOURCE_COVERAGE.relative_to(ROOT)),
            "input_hash": _hash(inputs),
        },
        "policy": {
            "fail_closed": True,
            "descriptive_only": True,
            "no_persuasion": True,
            "no_microtargeting": True,
            "no_hidden_imputation": True,
            "no_national_to_territorial_inference": True,
            "no_outcome_probability_claim": True,
        },
    }
    state["state_hash"] = _hash(state)
    return state


def write_situation_state(*, as_of: datetime | None = None) -> Path:
    state = build_situation_state(as_of=as_of)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return OUTPUT


__all__ = ["SituationStateBlocked", "build_situation_state", "write_situation_state"]
