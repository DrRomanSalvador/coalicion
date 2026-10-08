"""Neutral situation-room summaries built only from materialized evidence."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

MADRID = ZoneInfo("Europe/Madrid")


def evidence_level(poll: dict[str, Any]) -> str:
    tier = str(poll.get("source_tier", "")).upper()
    validation = str(poll.get("validation", "")).upper()
    complete = all([
        poll.get("fieldwork_start"),
        poll.get("fieldwork_end"),
        poll.get("sample_size"),
        poll.get("methodology"),
    ])
    if tier.startswith("PRIMARY") and validation in {"PRIMARY_VERIFIED", "PRIMARY_VERIFIABLE"} and complete:
        return "PRIMARY_VERIFICABLE"
    if tier == "SECONDARY_REPLICA":
        return "SECONDARY_REPLICA"
    if complete:
        return "STRUCTURALLY_COMPLETE"
    return "INCOMPLETE"


def situation(state: dict[str, Any], polls: list[dict[str, Any]], sources: list[dict[str, Any]], *, now: datetime | None = None) -> str:
    now = now or datetime.now(MADRID)
    counts: dict[str, int] = {}
    for source in sources:
        status = str(source.get("status", source.get("health", "UNKNOWN"))).upper()
        counts[status] = counts.get(status, 0) + 1
    primary = sum(evidence_level(p) == "PRIMARY_VERIFICABLE" for p in polls)
    secondary = sum(evidence_level(p) == "SECONDARY_REPLICA" for p in polls)
    incomplete = sum(evidence_level(p) == "INCOMPLETE" for p in polls)
    territorial = sum(bool(p.get("territorial")) for p in polls)
    failures = state.get("last_failures") or []
    coverage = state.get("last_coverage") or {}
    failed = counts.get("FAILED", 0) + counts.get("ERROR", 0)
    degraded = counts.get("DEGRADED", 0)
    operational = sum(counts.get(x, 0) for x in ("OK", "UP", "HEALTHY", "ACTIVE"))
    status = "LIMITADO" if failed or coverage.get("blockers") else ("OPERATIVO" if sources else "BLOQUEADO")
    lines = [
        "🧭 SALA DE SITUACIÓN · TIEMPO REAL", "",
        f"Corte: {now.strftime('%Y-%m-%d %H:%M %Z')}",
        f"Estado: {status}", "",
        "FUENTES",
        f"• Registradas: {len(sources)} · comprobadas: {len(sources)} · operativas: {operational} · degradadas: {degraded} · fallidas: {failed}",
        f"• Última comprobación materializada: {state.get('last_run', 'n/d')}", "",
        "EVIDENCIA",
        f"• Observaciones registradas: {len(polls)}",
        f"• Primarias verificables: {primary} · secundarias: {secondary} · incompletas: {incomplete}",
        f"• Territoriales explícitas: {territorial}/{len(polls)}", "",
        "COBERTURA",
        f"• {coverage.get('claim', 'n/d')}",
        f"• Bloqueadores: {len(coverage.get('blockers') or [])}", "",
        "LIMITACIONES",
        "• No se convierte una encuesta nacional en escaños provinciales.",
        "• No se publican intervalos/probabilidades bayesianas sin posterior y calibración materializados.",
        "• Las observaciones secundarias no equivalen a verificación primaria.",
    ]
    if failures:
        lines += ["", "INCIDENCIAS"]
        lines += [f"• {x.get('source_id', 'fuente')}: {x.get('error', 'incidencia')}" for x in failures[:6]]
    return "\n".join(lines)


def trends(polls: list[dict[str, Any]]) -> str:
    if len(polls) < 2:
        return "📈 TENDENCIAS\n\nNo hay suficientes observaciones fechadas."
    current, reference = polls[0], polls[-1]
    a = current.get("parties") if isinstance(current.get("parties"), dict) else {}
    b = reference.get("parties") if isinstance(reference.get("parties"), dict) else {}
    rows = []
    for party in set(a) | set(b):
        try:
            rows.append((abs(float(a.get(party, 0)) - float(b.get(party, 0))), party, float(a.get(party, 0)) - float(b.get(party, 0))))
        except (TypeError, ValueError):
            pass
    rows.sort(key=lambda x: (-x[0], x[1]))
    lines = ["📈 TENDENCIAS · DESCRIPTIVAS", "", f"Ventana: {reference.get('publication_date', 'n/d')} → {current.get('publication_date', 'n/d')}", "Sin atribución causal ni posterior bayesiano.", ""]
    lines += [f"• {party}: {delta:+.1f} pp" for _, party, delta in rows[:12]]
    return "\n".join(lines)


def uncertainty(estimation: dict[str, Any]) -> str:
    value = estimation.get("uncertainty")
    if not isinstance(value, dict) or not value:
        return "📐 INCERTIDUMBRE\n\nNo hay posterior/calibración probabilística materializada. No se inventan intervalos, probabilidades ni MAE."
    import json
    return "📐 INCERTIDUMBRE\n\n" + json.dumps(value, ensure_ascii=False, indent=2)
