"""Deterministic operational briefing for the neutral electoral monitoring layer."""
from __future__ import annotations

from datetime import date
from typing import Any

from src.election_calendar import critical_window


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _item(priority: str, code: str, title: str, detail: str, due: str | None = None,
          source: str | None = None, freshness: str | None = None) -> dict[str, Any]:
    return {
        "priority": priority,
        "code": code,
        "title": title,
        "detail": detail,
        "due": due,
        "source": source,
        "freshness": freshness,
    }


def build_briefing(
    *,
    as_of: date,
    polls: list[dict[str, Any]],
    sources: list[dict[str, Any]],
    observations: dict[str, Any] | None = None,
    horizon_days: int = 31,
) -> list[dict[str, Any]]:
    """Return only factual, actionable monitoring items; never invent estimates."""
    observations = observations or {}
    items: list[dict[str, Any]] = []

    for event in critical_window(as_of, horizon_days):
        if event["status"] == "past":
            continue
        days = int(event["days_remaining"])
        priority = "CRITICAL" if days <= 2 else "HIGH" if days <= 7 else "MEDIUM"
        when = "hoy" if days == 0 else f"en {days} días"
        items.append(_item(
            priority,
            f"LEGAL_{event['code']}",
            event["title"],
            f"Vence {when}.",
            due=event["date"],
            source=event["source"],
        ))

    if not polls:
        items.append(_item(
            "HIGH",
            "POLL_COVERAGE",
            "No hay sondeos validados disponibles",
            "Revisar las fuentes de encuestas y la última observación materializada.",
        ))
    else:
        dated = [(p, _parse_date(p.get("publication_date"))) for p in polls]
        dated = [(p, d) for p, d in dated if d is not None]
        if dated:
            latest = max(d for _, d in dated)
            age = (as_of - latest).days
            if age >= 7:
                items.append(_item(
                    "HIGH",
                    "POLL_STALENESS",
                    "La última observación de sondeos está envejecida",
                    f"Última publicación: {latest.isoformat()} ({age} días).",
                    freshness=f"{age}d",
                ))
            elif age >= 3:
                items.append(_item(
                    "MEDIUM",
                    "POLL_STALENESS",
                    "La última observación de sondeos empieza a perder frescura",
                    f"Última publicación: {latest.isoformat()} ({age} días).",
                    freshness=f"{age}d",
                ))

    failed: list[str] = []
    for source in sources:
        status = str(source.get("status", source.get("health", ""))).upper()
        if status in {"DOWN", "FAILED", "ERROR", "DEGRADED", "UNHEALTHY"}:
            failed.append(str(source.get("id", source.get("source_id", source.get("name", "?")))))
    if failed:
        items.append(_item(
            "HIGH",
            "SOURCE_HEALTH",
            f"{len(failed)} fuente(s) con incidencia",
            "La vigilancia debe mantenerlas identificadas y recuperar evidencia por las vías disponibles.",
            source=", ".join(failed[:12]),
        ))

    territorial = int(observations.get("territorial_poll_count", 0) or 0)
    if polls and territorial == 0:
        items.append(_item(
            "HIGH",
            "TERRITORIAL_INPUT",
            "No hay observaciones territoriales explícitas recientes",
            "No publicar escaños actuales desde porcentajes nacionales; buscar evidencia provincial explícita.",
        ))

    items.sort(key=lambda x: (
        {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "INFO": 3}.get(x["priority"], 9),
        x["due"] or "9999-12-31",
        x["code"],
    ))
    return items
