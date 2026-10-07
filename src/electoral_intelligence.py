"""Radar electoral neutral: cambios verificables que requieren atención operativa.

No recomienda partidos, coaliciones ni acciones políticas. Consume resultados ya
validados por los motores canónicos y convierte cambios relevantes en alertas
descriptivas, trazables y reproducibles.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date
from typing import Any, Mapping, Sequence
import hashlib
import json


VERSION = "1.0"
ELECTION_DATE_2026 = date(2026, 11, 29)
COALITION_REGISTRATION_DEADLINE_2026 = date(2026, 10, 16)
CANDIDATURE_REGISTRATION_START_2026 = date(2026, 10, 21)
CANDIDATURE_REGISTRATION_DEADLINE_2026 = date(2026, 10, 26)
CANDIDATURE_PROCLAMATION_2026 = date(2026, 11, 2)
CAMPAIGN_START_2026 = date(2026, 11, 13)
CAMPAIGN_END_2026 = date(2026, 11, 27)
POLL_PUBLICATION_LAST_DAY_2026 = date(2026, 11, 23)
REFLECTION_DAY_2026 = date(2026, 11, 28)
CONSTITUTIVE_SESSION_2026 = date(2026, 12, 23)


@dataclass(frozen=True)
class Alert:
    code: str
    severity: str
    title: str
    facts: Mapping[str, Any]
    evidence: tuple[str, ...] = ()
    reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _deadline_alerts(today: date) -> list[Alert]:
    milestones = [
        ("COALITION_DEADLINE", COALITION_REGISTRATION_DEADLINE_2026, "Cierre de comunicación de coaliciones"),
        ("CANDIDATURES_OPEN", CANDIDATURE_REGISTRATION_START_2026, "Inicio de presentación de candidaturas"),
        ("CANDIDATURES_DEADLINE", CANDIDATURE_REGISTRATION_DEADLINE_2026, "Cierre de presentación de candidaturas"),
        ("CANDIDATURES_PROCLAIMED", CANDIDATURE_PROCLAMATION_2026, "Proclamación de candidaturas"),
        ("CAMPAIGN_START", CAMPAIGN_START_2026, "Inicio de campaña"),
        ("POLLING_DEADLINE", POLL_PUBLICATION_LAST_DAY_2026, "Último día de difusión legal de sondeos"),
        ("CAMPAIGN_END", CAMPAIGN_END_2026, "Fin de campaña"),
        ("REFLECTION_DAY", REFLECTION_DAY_2026, "Jornada de reflexión"),
        ("ELECTION_DAY", ELECTION_DATE_2026, "Elecciones generales"),
        ("CONSTITUTIVE_SESSION", CONSTITUTIVE_SESSION_2026, "Sesión constitutiva de las Cámaras"),
    ]
    alerts: list[Alert] = []
    for code, when, title in milestones:
        days = (when - today).days
        if days < 0:
            continue
        if days <= 14:
            severity = "CRITICAL" if days <= 2 else "ALERT"
            alerts.append(Alert(
                code=f"DEADLINE_{code}",
                severity=severity,
                title=title,
                facts={"date": when.isoformat(), "days_remaining": days},
                reason="Hito electoral dentro de los próximos 14 días.",
            ))
    return alerts


def compare_national_state(previous: Mapping[str, Any], current: Mapping[str, Any],
                           *, vote_threshold: float = 0.005,
                           seat_threshold: int = 1) -> list[Alert]:
    """Detecta cambios nacionales sin interpretarlos como tendencia electoral."""
    alerts: list[Alert] = []
    parties = sorted(set(previous) | set(current))
    for party in parties:
        old = previous.get(party, {})
        new = current.get(party, {})
        vote_change = _number(new.get("vote_share")) - _number(old.get("vote_share"))
        seat_change = int(new.get("seats", 0)) - int(old.get("seats", 0))
        if abs(vote_change) >= vote_threshold or abs(seat_change) >= seat_threshold:
            alerts.append(Alert(
                code="NATIONAL_STATE_CHANGE",
                severity="ALERT",
                title=f"Cambio nacional observado: {party}",
                facts={
                    "party": party,
                    "vote_share_change": vote_change,
                    "seat_change": seat_change,
                    "previous": dict(old),
                    "current": dict(new),
                },
                reason="Cambio supera al menos uno de los umbrales configurados.",
            ))
    return alerts


def detect_marginality_changes(previous: Sequence[Mapping[str, Any]],
                               current: Sequence[Mapping[str, Any]],
                               *, vote_threshold: int = 25) -> list[Alert]:
    """Detecta circunscripciones cuyo escaño marginal ha cambiado materialmente."""
    old = {x["constituency"]: x for x in previous}
    new = {x["constituency"]: x for x in current}
    alerts: list[Alert] = []
    for constituency in sorted(set(old) | set(new)):
        a, b = old.get(constituency), new.get(constituency)
        if not a or not b:
            alerts.append(Alert(
                code="MARGINALITY_MAP_CHANGE",
                severity="ALERT",
                title=f"Cambio de mapa marginal: {constituency}",
                facts={"constituency": constituency, "previous": a, "current": b},
                reason="La circunscripción entra o sale del conjunto marginal.",
            ))
            continue
        delta_votes = int(b.get("votes_to_change", 0)) - int(a.get("votes_to_change", 0))
        holder_changed = a.get("last_seat_holder") != b.get("last_seat_holder")
        challenger_changed = a.get("challenger") != b.get("challenger")
        if abs(delta_votes) >= vote_threshold or holder_changed or challenger_changed:
            alerts.append(Alert(
                code="MARGINALITY_CHANGE",
                severity="ALERT",
                title=f"Cambio de marginalidad: {constituency}",
                facts={
                    "constituency": constituency,
                    "votes_to_change_change": delta_votes,
                    "holder_changed": holder_changed,
                    "challenger_changed": challenger_changed,
                    "previous": dict(a),
                    "current": dict(b),
                },
                reason="Cambia el margen de desplazamiento o la identidad de las candidaturas implicadas.",
            ))
    return alerts


def detect_coalition_changes(previous: Mapping[str, Any], current: Mapping[str, Any],
                             *, seat_threshold: int = 1) -> list[Alert]:
    """Detecta cambios descriptivos en un contrafactual de coalición."""
    alerts: list[Alert] = []
    old = _number(previous.get("coalition_seats"))
    new = _number(current.get("coalition_seats"))
    old_sep = _number(previous.get("separate_seats"))
    new_sep = _number(current.get("separate_seats"))
    delta = (new - new_sep) - (old - old_sep)
    if abs(delta) >= seat_threshold:
        alerts.append(Alert(
            code="COALITION_COUNTERFACTUAL_CHANGE",
            severity="ALERT",
            title="Cambio en el resultado electoral del contrafactual de coalición",
            facts={
                "previous": dict(previous),
                "current": dict(current),
                "coalition_delta_change": delta,
            },
            reason="El resultado recalculado por circunscripción ha cambiado.",
        ))
    return alerts


def detect_uncertainty_changes(previous: Mapping[str, Any], current: Mapping[str, Any],
                               *, seat_width_threshold: float = 1.0) -> list[Alert]:
    """Detecta cambios en intervalos de escaños, sin convertirlos en probabilidades de victoria."""
    alerts: list[Alert] = []
    for party in sorted(set(previous) | set(current)):
        a, b = previous.get(party, {}), current.get(party, {})
        old_width = _number(a.get("max")) - _number(a.get("min"))
        new_width = _number(b.get("max")) - _number(b.get("min"))
        if abs(new_width - old_width) >= seat_width_threshold:
            alerts.append(Alert(
                code="UNCERTAINTY_CHANGE",
                severity="WARNING",
                title=f"Cambio de incertidumbre: {party}",
                facts={
                    "party": party,
                    "previous_interval_width": old_width,
                    "current_interval_width": new_width,
                    "previous": dict(a),
                    "current": dict(b),
                },
                reason="Cambia materialmente el ancho del intervalo de simulación.",
            ))
    return alerts


def source_health_alerts(sources: Sequence[Mapping[str, Any]]) -> list[Alert]:
    """Convierte estados de fuente en alertas separando fallo de dato de fallo de infraestructura."""
    alerts: list[Alert] = []
    for source in sources:
        status = str(source.get("status", "")).upper()
        if status in {"DOWN", "FAILED", "ERROR"}:
            severity = "CRITICAL" if source.get("coverage_role") == "primary" else "WARNING"
            alerts.append(Alert(
                code="SOURCE_HEALTH",
                severity=severity,
                title=f"Fuente no disponible: {source.get('id', 'unknown')}",
                facts={
                    "source_id": source.get("id"),
                    "coverage_role": source.get("coverage_role"),
                    "status": status,
                    "failure_streak": source.get("failure_streak"),
                    "last_success": source.get("last_success"),
                },
                reason="La salud de la fuente cambió; no se sustituye silenciosamente su evidencia.",
            ))
    return alerts


def build_monthly_radar(*, today: date,
                        national_previous: Mapping[str, Any] | None = None,
                        national_current: Mapping[str, Any] | None = None,
                        marginality_previous: Sequence[Mapping[str, Any]] | None = None,
                        marginality_current: Sequence[Mapping[str, Any]] | None = None,
                        coalition_previous: Mapping[str, Any] | None = None,
                        coalition_current: Mapping[str, Any] | None = None,
                        uncertainty_previous: Mapping[str, Any] | None = None,
                        uncertainty_current: Mapping[str, Any] | None = None,
                        sources: Sequence[Mapping[str, Any]] = (),
                        evidence_refs: Sequence[str] = ()) -> dict[str, Any]:
    """Construye el radar mensual operativo a partir de hechos ya calculados."""
    alerts: list[Alert] = _deadline_alerts(today)
    if national_previous is not None and national_current is not None:
        alerts.extend(compare_national_state(national_previous, national_current))
    if marginality_previous is not None and marginality_current is not None:
        alerts.extend(detect_marginality_changes(marginality_previous, marginality_current))
    if coalition_previous is not None and coalition_current is not None:
        alerts.extend(detect_coalition_changes(coalition_previous, coalition_current))
    if uncertainty_previous is not None and uncertainty_current is not None:
        alerts.extend(detect_uncertainty_changes(uncertainty_previous, uncertainty_current))
    alerts.extend(source_health_alerts(sources))

    severity_order = {"CRITICAL": 0, "ALERT": 1, "WARNING": 2, "INFO": 3}
    alerts.sort(key=lambda x: (severity_order.get(x.severity, 9), x.code, x.title))
    payload = {
        "version": VERSION,
        "status": "OK",
        "as_of": today.isoformat(),
        "election_date": ELECTION_DATE_2026.isoformat(),
        "alert_count": len(alerts),
        "alerts": [x.as_dict() for x in alerts],
        "evidence_refs": list(evidence_refs),
        "traceability": {"input_hash": _hash({
            "today": today.isoformat(),
            "national_previous": national_previous,
            "national_current": national_current,
            "marginality_previous": marginality_previous,
            "marginality_current": marginality_current,
            "coalition_previous": coalition_previous,
            "coalition_current": coalition_current,
            "uncertainty_previous": uncertainty_previous,
            "uncertainty_current": uncertainty_current,
            "sources": sources,
            "evidence_refs": evidence_refs,
        })},
        "policy": {
            "descriptive_only": True,
            "no_recommendations": True,
            "no_rankings": True,
            "no_vote_transfer_inference": True,
            "no_national_to_territorial_inference": True,
            "no_outcome_probability_claim": True,
        },
    }
    payload["traceability"]["output_hash"] = _hash(payload)
    return payload


__all__ = [
    "Alert",
    "build_monthly_radar",
    "compare_national_state",
    "detect_marginality_changes",
    "detect_coalition_changes",
    "detect_uncertainty_changes",
    "source_health_alerts",
]
