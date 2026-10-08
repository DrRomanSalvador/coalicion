"""Operational Telegram interface for the neutral COALICIÓN evidence pipeline."""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any
from datetime import date

from src.election_calendar import critical_window
from src.operational_briefing import build_briefing

import requests

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "artifacts/poll_monitor_state.json"
OBSERVATIONS = ROOT / "artifacts/estimation/observations.json"
ESTIMATION = ROOT / "artifacts/estimation/real_estimation.json"
EXECUTION = ROOT / "artifacts/execution_state.json"
OOS = ROOT / "artifacts/oos_historical_2004_2023.json"
SNAPSHOT = ROOT / "artifacts/decision_snapshot.json"
SCENARIO_DIR = ROOT / "artifacts"
API_TIMEOUT = 40
API_RETRIES = 4
MAX_MESSAGE = 4090

COMMANDS = [
    ("hoy", "¿Qué está pasando ahora?"),
    ("briefing", "¿Qué debo saber ahora mismo?"),
    ("mes", "¿Qué importa este mes?"),
    ("cambios", "¿Qué ha cambiado?"),
    ("encuestas", "¿Qué dicen los sondeos?"),
    ("escanos", "¿Qué implican en escaños?"),
    ("mayorias", "¿Qué mayorías son aritméticamente posibles?"),
    ("coaliciones", "¿Qué combinaciones son aritméticamente posibles?"),
    ("territorio", "¿Dónde están los cambios?"),
    ("calendario", "¿Qué plazos importan?"),
    ("fuentes", "¿Qué fuentes están activas?"),
    ("evidencia", "¿De dónde sale cada dato?"),
    ("escenarios", "¿Qué escenarios están calculados?"),
    ("auditoria", "¿Qué nivel de verificación tiene?"),
    ("estado", "Estado operativo"),
    ("urgencias", "¿Qué requiere atención?"),
    ("radar", "Radar de novedades"),
    ("menu", "Menú completo"),
    ("ayuda", "Ayuda"),
]


class TelegramBotError(RuntimeError):
    pass


def _token() -> str:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token or token == "TU_TOKEN_AQUI":
        raise TelegramBotError("TELEGRAM_BOT_TOKEN is required")
    return token


def _api(method: str, **kwargs: Any) -> dict[str, Any]:
    last: Exception | None = None
    for attempt in range(API_RETRIES):
        try:
            response = requests.post(
                f"https://api.telegram.org/bot{_token()}/{method}",
                timeout=API_TIMEOUT,
                **kwargs,
            )
            response.raise_for_status()
            payload = response.json()
            if not payload.get("ok"):
                raise TelegramBotError(f"Telegram API error: {payload}")
            return payload
        except (requests.RequestException, ValueError) as exc:
            last = exc
            if attempt + 1 < API_RETRIES:
                time.sleep(min(2**attempt, 8))
    raise TelegramBotError(f"Telegram transport failed after {API_RETRIES} attempts: {last}") from last


def _safe_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _list_records(value: Any) -> list[dict[str, Any]]:
    return [x for x in value if isinstance(x, dict)] if isinstance(value, list) else []


def _observations() -> dict[str, Any]:
    return _safe_json(OBSERVATIONS)


def _latest_polls() -> list[dict[str, Any]]:
    rows = _list_records(_observations().get("polls"))
    if not rows:
        state = _safe_json(STATE)
        rows = _list_records(state.get("validated_polls") or state.get("polls"))
    return sorted(rows, key=lambda x: str(x.get("publication_date", "")), reverse=True)


def _sources() -> list[dict[str, Any]]:
    value = _safe_json(STATE).get("sources") or _safe_json(STATE).get("source_health")
    if isinstance(value, dict):
        return [{"id": k, **(v if isinstance(v, dict) else {"status": v})} for k, v in value.items()]
    return _list_records(value)


def _fmt_number(value: Any, suffix: str = "") -> str:
    try:
        return f"{float(value):.1f}{suffix}"
    except (TypeError, ValueError):
        return "n/d"


def _delta(current: dict[str, Any], previous: dict[str, Any], party: str) -> str:
    try:
        return f"{float(current.get(party, 0)) - float(previous.get(party, 0)):+.1f} pp"
    except (TypeError, ValueError):
        return "n/d"


def _public_text(text: str) -> str:
    """Sanitize internal vocabulary without hiding substantive factual content."""
    value = str(text or "").strip()
    if not value:
        return "🟦 COALICIÓN\n\nEstado verificable disponible en /hoy."
    value = re.sub(r"(?i)blocked(?:[_-][a-z0-9_-]+)*", "COMPROBACIÓN PENDIENTE", value)
    value = re.sub(r"(?i)\bbloquead[oa]?\b|\bbloqueo\b", "COMPROBACIÓN PENDIENTE", value)
    value = re.sub(r"(?i)\berror\b|\bexception\b", "COMPROBACIÓN PENDIENTE", value)
    value = re.sub(r"(?i)not[_-]strictly[_-]certified", "VERIFICACIÓN OOS PENDIENTE", value)
    return value


def _answer_callback(callback_id: str) -> None:
    """Acknowledge an inline-button callback without exposing transport details."""
    try:
        _api("answerCallbackQuery", json={"callback_query_id": callback_id})
    except TelegramBotError:
        pass


def _send(chat_id: int, text: str, markup: dict[str, Any] | None = None) -> None:
    """Send complete public content in Telegram-safe chunks."""
    value = _public_text(text)
    chunks: list[str] = []
    current = ""
    for line in value.splitlines(keepends=True):
        if len(current) + len(line) <= MAX_MESSAGE:
            current += line
            continue
        if current:
            chunks.append(current.rstrip())
            current = ""
        while len(line) > MAX_MESSAGE:
            cut = line.rfind(" ", 0, MAX_MESSAGE + 1)
            cut = cut if cut > 0 else MAX_MESSAGE
            chunks.append(line[:cut].rstrip())
            line = line[cut:].lstrip()
        current = line
    if current.strip():
        chunks.append(current.rstrip())
    if not chunks:
        chunks = [value]
    for index, chunk in enumerate(chunks):
        payload: dict[str, Any] = {"chat_id": chat_id, "text": chunk}
        if markup and index == 0:
            payload["reply_markup"] = markup
        _api("sendMessage", json=payload)

def _briefing_text() -> str:
    """Single-screen factual situation room for current electoral operations."""
    today = date.today()
    polls = _latest_polls()
    sources = _sources()
    observations = _observations()
    briefing = build_briefing(
        as_of=today,
        polls=polls,
        sources=sources,
        observations=observations,
        horizon_days=14,
    )
    latest = polls[0] if polls else {}
    source_ok = 0
    source_attention = 0
    for source in sources:
        status = str(source.get("status", source.get("health", "UNKNOWN"))).upper()
        if status in {"OK", "UP", "HEALTHY", "ACTIVE"}:
            source_ok += 1
        elif status in {"DOWN", "FAILED", "ERROR", "DEGRADED", "UNHEALTHY"}:
            source_attention += 1

    lines = [
        "🧭 COALICIÓN · SALA DE SITUACIÓN",
        "",
        "HOY",
        f"• Elecciones: 29/11/2026 · 350 escaños · 52 circunscripciones",
        f"• Sondeos validados: {len(polls)}",
        f"• Fuentes registradas: {len(sources)} · activas: {source_ok} · con seguimiento: {source_attention}",
    ]
    if latest:
        lines.extend([
            "",
            "ÚLTIMA OBSERVACIÓN",
            f"• {latest.get('publication_date', 'n/d')} · {latest.get('pollster', latest.get('source', 'fuente no indicada'))}",
        ])
        parties = latest.get("parties")
        if isinstance(parties, dict):
            values = []
            for party, value in parties.items():
                try:
                    values.append((str(party), float(value)))
                except (TypeError, ValueError):
                    pass
            values.sort(key=lambda x: (-x[1], x[0]))
            if values:
                lines.append("• " + " · ".join(f"{p} {v:.1f}%" for p, v in values[:6]))
    else:
        lines.extend(["", "ÚLTIMA OBSERVACIÓN", "• No hay un sondeo validado reciente que publicar."])

    lines.extend(["", "PRÓXIMO HITO"])
    upcoming = [x for x in critical_window(today, horizon_days=14) if x["status"] != "past"]
    if upcoming:
        e = upcoming[0]
        lines.append(f"• {e['date']} · {e['title']} · {e['days_remaining']} días")
    else:
        lines.append("• No hay un hito legal dentro de los próximos 14 días.")

    lines.extend(["", "LO QUE REQUIERE ATENCIÓN"])
    if briefing:
        for item in briefing[:4]:
            lines.append(f"• {item['priority']} · {item['title']}")
            lines.append(f"  {item['detail']}")
    else:
        lines.append("• No se ha detectado una novedad operativa materializada.")

    lines.extend([
        "",
        "LÍMITES DE LECTURA",
        "• Los porcentajes nacionales no se convierten automáticamente en escaños provinciales.",
        "• Las combinaciones parlamentarias se calculan solo sobre composiciones explícitas.",
        "• Cada observación se interpreta con su fecha y fuente.",
        "",
        "Pregunta siguiente: «¿qué ha cambiado?», «¿qué vence?», «¿de dónde sale este dato?» o «¿qué implican los sondeos en escaños?»",
    ])
    return "\n".join(lines)


def _month_text() -> str:
    """Executive neutral briefing for the current election month."""
    today = date.today()
    polls = _latest_polls()
    sources = _sources()
    briefing = build_briefing(
        as_of=today,
        polls=polls,
        sources=sources,
        observations=_observations(),
        horizon_days=31,
    )
    lines = [
        "🗓 OCTUBRE · CENTRO DE SITUACIÓN",
        "",
        "ELECCIÓN: 29/11/2026 · 350 escaños · 52 circunscripciones",
        "",
        "PRIORIDADES OPERATIVAS",
    ]
    for item in briefing[:8]:
        due = f" · vence {item['due']}" if item.get("due") else ""
        lines.append(f"• {item['priority']} · {item['title']}{due}")
        lines.append(f"  {item['detail']}")
    lines.extend([
        "",
        "DATOS DE COBERTURA",
        f"• Sondeos validados: {len(polls)}",
        f"• Fuentes registradas: {len(sources)}",
        "",
        "CAPACIDADES",
        "• Sondeos: seguimiento fechado y comparación.",
        "• Territorio: solo con evidencia provincial explícita.",
        "• Escaños: D’Hondt por circunscripción, sin inferencia nacional→territorial.",
        "• Mayorías/combinaciones: aritmética descriptiva sobre composiciones explícitas.",
        "• Evidencia: fuente + fecha + registro.",
    ])
    return "\n".join(lines)

def _home_text() -> str:
    polls = _latest_polls()
    estimation = _safe_json(ESTIMATION)
    radar = estimation.get("radar") or {}
    alerts = _list_records(radar.get("alerts"))
    latest = polls[0] if polls else {}
    parties = latest.get("parties") if isinstance(latest.get("parties"), dict) else {}
    parsed = []
    for party, value in parties.items():
        try:
            parsed.append((str(party), float(value)))
        except (TypeError, ValueError):
            continue
    parsed.sort(key=lambda x: (-x[1], x[0]))
    top = " · ".join(f"{p} {v:.1f}%" for p, v in parsed[:6])
    lines = [
        "🟦 COALICIÓN · PANEL DE HOY",
        "",
        f"Último sondeo validado: {latest.get('publication_date', 'n/d')} · {latest.get('pollster', '?')}" if latest else "Último sondeo validado: n/d",
        top or "Sin estimaciones publicadas en los registros disponibles.",
        "",
        f"Novedades relevantes: {len(alerts)}",
    ]
    for alert in alerts[:4]:
        lines.append(f"• {alert.get('title', alert.get('code', 'Novedad'))}")
    lines.extend([
        "",
        "Elige una pregunta. El sistema responde con el dato más reciente y verificable disponible.",
        "Los controles internos de calidad no se muestran como errores al usuario.",
    ])
    return "\n".join(lines)


def _majorities_text() -> str:
    snapshot = _safe_json(SNAPSHOT)
    projection = snapshot.get("projection")
    if not isinstance(projection, dict):
        return (
            "🏛 MAYORÍAS · ARITMÉTICA\n\n"
            "Referencia parlamentaria: 350 escaños.\n"
            "Mayoría absoluta: 176.\n\n"
            "La mayoría absoluta es de 176 escaños. "
            "La atribución actual a partidos requiere una composición territorial explícita."
        )
    seats = projection.get("national_seats") or projection.get("party") or {}
    rows = []
    for party, value in seats.items():
        try:
            rows.append((str(party), int(value)))
        except (TypeError, ValueError):
            continue
    rows.sort(key=lambda x: (-x[1], x[0]))
    total = sum(v for _, v in rows)
    if not rows:
        return "🏛 MAYORÍAS · ARITMÉTICA\n\nNo hay composición de escaños materializada."
    return (
        "🏛 MAYORÍAS · ARITMÉTICA\n\n"
        + "\n".join(f"{p}: {s}" for p, s in rows)
        + f"\n\nTotal representado: {total}/350.\n"
        "Las combinaciones se tratan como aritmética descriptiva, no como recomendación política."
    )


def _coalitions_text() -> str:
    snapshot = _safe_json(SNAPSHOT)
    projection = snapshot.get("projection")
    seats = projection.get("national_seats") if isinstance(projection, dict) else None
    if not isinstance(seats, dict) or not seats:
        return (
            "🤝 COMBINACIONES · ARITMÉTICA\n\n"
            "Las combinaciones se calculan sobre una composición explícita de escaños. "
            "Los porcentajes nacionales no se convierten automáticamente en escaños."
        )
    rows = []
    for party, value in seats.items():
        try:
            rows.append((str(party), int(value)))
        except (TypeError, ValueError):
            continue
    rows.sort(key=lambda x: (-x[1], x[0]))
    combinations = []
    from itertools import combinations
    for size in range(2, min(4, len(rows)) + 1):
        for combo in combinations(rows, size):
            total = sum(v for _, v in combo)
            if total >= 176:
                combinations.append((size, total, combo))
    combinations.sort(key=lambda x: (x[0], x[1], tuple(p for p, _ in x[2])))
    if not combinations:
        return "🤝 COMBINACIONES · ARITMÉTICA\n\nNo hay combinación de 2–4 grupos que alcance 176 en la composición materializada."
    lines = ["🤝 COMBINACIONES · ARITMÉTICA", ""]
    for _, total, combo in combinations[:12]:
        lines.append(" + ".join(p for p, _ in combo) + f" = {total}")
    lines.append("")
    lines.append("Listado descriptivo, sin ordenar por conveniencia política.")
    return "\n".join(lines)


def _calendar_text() -> str:
    events = critical_window(date.today(), horizon_days=31)
    upcoming = [x for x in events if x["status"] != "past"]
    if not upcoming:
        return "📅 CALENDARIO · PRÓXIMOS HITOS\n\nNo hay hitos próximos en la ventana de 31 días."
    lines = ["📅 CALENDARIO · PRÓXIMOS HITOS", ""]
    for event in upcoming[:14]:
        d = event["days_remaining"]
        when = "hoy" if d == 0 else f"en {d} días"
        lines.append(f"• {event['date']} · {event['title']} · {when}")
    lines.extend(["", "Base: calendario legal derivado de la convocatoria oficial y LOREG."])
    return "\n".join(lines)

def _evidence_text() -> str:
    polls = _latest_polls()
    sources = _sources()
    source_ids = []
    for poll in polls[:5]:
        sid = poll.get("source_id") or poll.get("source") or poll.get("pollster")
        if sid and str(sid) not in source_ids:
            source_ids.append(str(sid))
    lines = [
        "🔎 EVIDENCIA · TRAZABILIDAD",
        "",
        f"Sondeos validados disponibles: {len(polls)}",
        f"Fuentes registradas por el monitor: {len(sources)}",
        "",
        "Fuentes de las observaciones recientes:",
    ]
    lines.extend(f"• {sid}" for sid in source_ids[:8]) if source_ids else lines.append("• no identificado en el registro")
    lines.extend([
        "",
        "Los datos se presentan como observación fechada; la fuente y el registro prevalecen sobre cualquier inferencia del bot.",
    ])
    return "\n".join(lines)


def _escanos_text() -> str:
    snapshot = _safe_json(SNAPSHOT)
    projection = snapshot.get("projection")
    if isinstance(projection, dict):
        seats = projection.get("national_seats") or projection.get("party") or {}
        rows = []
        for party, value in seats.items():
            try:
                rows.append((str(party), int(value)))
            except (TypeError, ValueError):
                continue
        rows.sort(key=lambda x: (-x[1], x[0]))
        if rows:
            return "🪑 ESCAÑOS · COMPOSICIÓN MATERIALIZADA\n\n" + "\n".join(f"{p}: {s}" for p, s in rows)
    return (
        "🪑 ESCAÑOS · SITUACIÓN ACTUAL\n\n"
        "La cifra actual de escaños requiere una distribución territorial explícita. "
        "El sistema no convierte automáticamente porcentajes nacionales en reparto territorial."
    )


def _natural_query(text: str) -> str | None:
    import unicodedata
    normalized = unicodedata.normalize("NFD", text.lower())
    normalized = "".join(c for c in normalized if unicodedata.category(c) != "Mn")
    rules = [
        (("/briefing", "que debo saber", "que debo saber ahora", "sala de situacion", "resumen ejecutivo"), "/briefing"),
        (("/hoy", "que pasa", "que esta pasando", "situacion actual", "panorama", "ahora"), "/hoy"),
        (("/mes", "este mes", "octubre", "que importa este mes", "que hay este mes"), "/mes"),
        (("/cambios", "que ha cambiado", "novedades", "cambios", "ultimas novedades"), "/cambios"),
        (("/encuestas", "sondeos", "encuestas", "que dicen los sondeos"), "/encuestas"),
        (("/escanos", "escanos", "cuantos escanos", "que implican"), "/escanos"),
        (("/mayorias", "mayoria", "mayorias", "176"), "/mayorias"),
        (("/coaliciones", "coalicion", "combinaciones", "pactos aritmeticos"), "/coaliciones"),
        (("/territorio", "donde", "territorio", "provincias", "circunscripciones"), "/territorio"),
        (("/calendario", "plazos", "fechas", "que plazos", "agenda"), "/calendario"),
        (("/fuentes", "fuentes", "que fuentes"), "/fuentes"),
        (("/evidencia", "evidencia", "de donde sale", "fuente del dato"), "/evidencia"),
        (("/escenarios", "escenarios", "supuestos"), "/escenarios"),
        (("/auditoria", "auditoria", "verificacion", "rigor"), "/auditoria"),
        (("/urgencias", "que requiere atencion", "que requiere atencion ahora", "incidencias"), "/urgencias"),
    ]
    for needles, command in rules:
        if any(needle in normalized for needle in needles):
            return command
    return None

def _menu_markup() -> dict[str, Any]:
    return {
        "inline_keyboard": [
            [{"text": "🧭 ¿Qué debo saber ahora?", "callback_data": "cmd:/briefing"},
             {"text": "🟦 ¿Qué pasa ahora?", "callback_data": "cmd:/hoy"}],
            [{"text": "🗓 ¿Qué importa este mes?", "callback_data": "cmd:/mes"}],
            [{"text": "📈 ¿Qué ha cambiado?", "callback_data": "cmd:/cambios"},
             {"text": "🚨 ¿Qué requiere atención?", "callback_data": "cmd:/urgencias"}],
            [{"text": "🗳 ¿Qué dicen los sondeos?", "callback_data": "cmd:/encuestas"},
             {"text": "🪑 ¿Qué implica en escaños?", "callback_data": "cmd:/escanos"}],
            [{"text": "🏛 ¿Qué mayorías son posibles?", "callback_data": "cmd:/mayorias"},
             {"text": "🤝 ¿Qué combinaciones hay?", "callback_data": "cmd:/coaliciones"}],
            [{"text": "🗺 ¿Dónde están los cambios?", "callback_data": "cmd:/territorio"},
             {"text": "📅 ¿Qué plazos importan?", "callback_data": "cmd:/calendario"}],
            [{"text": "🔎 ¿De dónde sale cada dato?", "callback_data": "cmd:/evidencia"},
             {"text": "🧪 ¿Qué escenarios hay?", "callback_data": "cmd:/escenarios"}],
            [{"text": "🛡 ¿Qué nivel de verificación tiene?", "callback_data": "cmd:/auditoria"},
             {"text": "📡 Radar", "callback_data": "cmd:/radar"}],
        ]
    }

def _help_text() -> str:
    return (
        "🟦 COALICIÓN · PREGUNTAS OPERATIVAS\n\n"
        "Puedes pulsar una pregunta o escribirla directamente.\n\n"
        + "\n".join(f"/{name} — {description}" for name, description in COMMANDS)
        + "\n\nRespuestas breves, fechadas y trazables. Los controles de calidad se ejecutan internamente."
    )

def _urgencies_text() -> str:
    briefing = build_briefing(
        as_of=date.today(),
        polls=_latest_polls(),
        sources=_sources(),
        observations=_observations(),
        horizon_days=31,
    )
    if not briefing:
        return "🚨 ATENCIÓN · PRIORIDAD\n\nNo hay incidencias relevantes materializadas."
    lines = ["🚨 ATENCIÓN · PRIORIDAD", ""]
    for item in briefing[:10]:
        due = f" · {item['due']}" if item.get("due") else ""
        lines.append(f"{item['priority']} · {item['title']}{due}")
        lines.append(f"• {item['detail']}")
        if item.get("source"):
            lines.append(f"  Evidencia: {item['source']}")
    lines.extend(["", "Hechos verificables y comprobaciones operativas; sin recomendaciones políticas."])
    return "\n".join(lines)

def _polls_text() -> str:
    polls = _latest_polls()
    if not polls:
        return "🗳 ENCUESTAS\n\nNo hay una observación validada reciente que publicar. Se conserva la vigilancia de fuentes."
    lines = [f"🗳 ENCUESTAS · {len(polls)} observaciones validadas", ""]
    for i, poll in enumerate(polls[:7]):
        parties = poll.get("parties")
        if not isinstance(parties, dict):
            continue
        parsed = []
        for party, value in parties.items():
            try:
                parsed.append((str(party), float(value)))
            except (TypeError, ValueError):
                continue
        parsed.sort(key=lambda x: (-x[1], x[0]))
        values = ", ".join(f"{p} {v:.1f}%" for p, v in parsed[:8]) or "sin porcentajes válidos"
        lines.append(f"{i + 1}. {poll.get('publication_date', '?')} · {poll.get('pollster', poll.get('source_id', '?'))}")
        lines.append(values)
        if i + 1 < len(polls):
            previous = polls[i + 1].get("parties")
            if isinstance(previous, dict):
                changes = ", ".join(
                    f"{p} {_delta(parties, previous, p)}"
                    for p in [x[0] for x in parsed[:6]]
                )
                if changes:
                    lines.append("Cambio vs anterior: " + changes)
        lines.append("")
    territory = sum(1 for poll in polls if poll.get("territorial"))
    lines.append(f"Territoriales explícitas: {territory}/{len(polls)}")
    if not territory:
        lines.append("ℹ️ Los sondeos disponibles son nacionales; no se publica una conversión automática a escaños.")
    return "\n".join(lines)


def _territory_text() -> str:
    obs = _observations()
    polls = _latest_polls()
    explicit = int(obs.get("territorial_poll_count", sum(1 for p in polls if p.get("territorial"))) or 0)
    return (
        "🗺 TERRITORIO\n\n"
        f"Observaciones nacionales: {obs.get('national_poll_count', len(polls))}\n"
        f"Observaciones territoriales explícitas: {explicit}\n"
        "Cobertura electoral: 52 circunscripciones / 350 escaños.\n\n"
        + ("🟢 Existe entrada territorial explícita en los artefactos observados."
           if explicit else
           "ℹ️ Cobertura territorial actual limitada: los escaños solo se calculan con evidencia provincial explícita. "
           "No se convierte automáticamente un porcentaje nacional en reparto provincial.")
    )


def _scenario_files() -> list[Path]:
    candidates = [
        SCENARIO_DIR / "scenario_central.json",
        SCENARIO_DIR / "scenario_optimista.json",
        SCENARIO_DIR / "scenario_pesimista.json",
    ]
    return [p for p in candidates if p.exists()]


def _scenarios_text() -> str:
    files = _scenario_files()
    if not files:
        return "🧪 ESCENARIOS\n\nNo hay escenarios materializados para publicar en este momento. No se fabrican valores."
    lines = ["🧪 ESCENARIOS MATERIALIZADOS", ""]
    for path in files:
        data = _safe_json(path)
        if not data:
            lines.append(f"• {path.name}: inválido o ilegible → no utilizable en este momento")
            continue
        lines.append(
            f"• {path.name}: "
            f"status={data.get('status', 'materializado')} · "
            f"schema={data.get('schema', 'n/d')}"
        )
    lines.append("")
    lines.append("Se muestran solo escenarios existentes; no se fabrican valores.")
    return "\n".join(lines)


def _sources_text() -> str:
    sources = _sources()
    if not sources:
        return "📡 FUENTES\n\nNo hay un estado reciente de fuentes publicado. No se inventa salud de fuentes; la vigilancia queda preparada para la próxima evidencia materializada."
    lines = ["📡 FUENTES · SALUD MATERIALIZADA", ""]
    for source in sources[:35]:
        sid = source.get("id", source.get("source_id", source.get("name", "?")))
        status = source.get("status", source.get("health", "UNKNOWN"))
        line = f"{sid}: {status}"
        lines.append(line)
    return "\n".join(lines)


def _human_oos_status(status: Any) -> str:
    value = str(status or "").strip().upper()
    return {
        "NOT_STRICTLY_CERTIFIED": "verificación OOS pendiente",
        "CERTIFIED": "verificado",
        "PASS": "verificado",
        "FAILED": "requiere revisión",
    }.get(value, "no determinado")


def _audit_text() -> str:
    execution = _safe_json(EXECUTION)
    oos = _safe_json(OOS)
    estimation = _safe_json(ESTIMATION)
    blocked = execution.get("blocked_tasks") or []
    warnings = execution.get("warnings") or []
    lines = [
        "🔎 AUDITORÍA · EVIDENCIA Y LIMITACIONES",
        "",
        f"Fase: {execution.get('current_phase', 'n/d')}",
        f"Estado OOS: {_human_oos_status(oos.get('status'))}",
        f"Elecciones OOS registradas: {oos.get('elections', 'n/d')}",
        f"Observaciones OOS: {oos.get('poll_observations', 'n/d')}",
        f"Estado de estimación: {_human_oos_status(estimation.get('status'))}",
        "",
        "CONTROL DE CALIDAD",
    ]
    lines.append(f"Comprobaciones pendientes: {len(blocked)}")
    lines.append(f"Advertencias registradas: {len(warnings)}")
    lines.append("")
    lines.append("Solo se publican resultados respaldados por evidencia materializada; lo no verificable queda fuera del resultado.")
    return "\n".join(lines)


def _radar_text() -> str:
    radar = _safe_json(ESTIMATION).get("radar") or {}
    alerts = _list_records(radar.get("alerts"))
    if not radar:
        return "📡 RADAR\nSin radar materializado."
    lines = [
        f"📡 RADAR · {radar.get('as_of', 'n/d')} · {_human_oos_status(radar.get('status'))}",
        f"Alertas materializadas: {len(alerts)}",
        "",
    ]
    for alert in alerts[:10]:
        lines.append(
            f"[{alert.get('priority', 'P4')}] {alert.get('title', '')} · "
            f"{alert.get('reason', '')}"
        )
    if str(_safe_json(ESTIMATION).get("status", "")).upper() in {"BLOCKED", "NOT_PROMOTED"}:
        lines.extend(["", "ℹ️ ALCANCE PREDICTIVO", "Los escaños solo se publican cuando existe distribución territorial explícita; mientras tanto se mantienen los datos verificables disponibles."])
    return "\n".join(lines)


def _changes_text() -> str:
    polls = _latest_polls()
    if len(polls) < 2:
        return "📈 CAMBIOS\n\nLa serie comparable aún no contiene dos observaciones fechadas suficientes para medir un cambio."
    current, previous = polls[0], polls[1]
    a = current.get("parties") if isinstance(current.get("parties"), dict) else {}
    b = previous.get("parties") if isinstance(previous.get("parties"), dict) else {}
    names = sorted(set(a) | set(b))
    changes = []
    for name in names:
        try:
            delta = float(a.get(name, 0)) - float(b.get(name, 0))
        except (TypeError, ValueError):
            continue
        if abs(delta) >= 0.5:
            changes.append((abs(delta), str(name), delta))
    changes.sort(key=lambda x: (-x[0], x[1]))
    lines = [
        "📈 CAMBIOS MATERIALES",
        "",
        f"Actual: {current.get('publication_date', 'n/d')} · {current.get('pollster', '?')}",
        f"Anterior: {previous.get('publication_date', 'n/d')} · {previous.get('pollster', '?')}",
        "",
    ]
    lines.extend(f"• {name}: {delta:+.1f} pp" for _, name, delta in changes[:12])
    if not changes:
        lines.append("• Ningún cambio ≥ 0,5 pp materializado.")
    lines.append("")
    lines.append("Solo compara observaciones; no interpreta causalidad.")
    return "\n".join(lines)


def _status_text() -> str:
    state = _safe_json(STATE)
    obs = _observations()
    estimation = _safe_json(ESTIMATION)
    polls = _latest_polls()
    sources = _sources()
    return (
        "🟢 ESTADO COALICIÓN\n\n"
        f"Monitor: {state.get('status', 'UNKNOWN')}\n"
        f"Observaciones validadas: {len(polls)}\n"
        f"Última publicación: {polls[0].get('publication_date', 'n/d') if polls else 'n/d'}\n"
        f"Fuentes registradas: {len(sources)}\n"
        f"Territoriales explícitas: {obs.get('territorial_poll_count', 0)}\n"
        f"Estado de estimación: {_human_oos_status(estimation.get('status'))}\n"
        "Verificación: OOS y calibración se muestran solo cuando están respaldados.\n"
        "Cobertura: sin datos sintéticos · sin inferencia nacional→territorial"
    )


def render_command(command: str) -> str:
    command = command.split("@", 1)[0].strip().lower()
    aliases = {
        "/start": "/briefing", "/menu": "/briefing", "/help": "/ayuda",
        "/prediccion": "/escanos", "/agenda": "/calendario",
    }
    command = aliases.get(command, command)
    renderers = {
        "/hoy": _home_text,
        "/briefing": _briefing_text,
        "/mes": _month_text,
        "/ayuda": _help_text,
        "/cambios": _changes_text,
        "/encuestas": _polls_text,
        "/escanos": _escanos_text,
        "/mayorias": _majorities_text,
        "/coaliciones": _coalitions_text,
        "/territorio": _territory_text,
        "/calendario": _calendar_text,
        "/fuentes": _sources_text,
        "/evidencia": _evidence_text,
        "/escenarios": _scenarios_text,
        "/auditoria": _audit_text,
        "/urgencias": _urgencies_text,
        "/estado": _status_text,
        "/radar": _radar_text,
    }
    renderer = renderers.get(command)
    return renderer() if renderer else "Comando no reconocido. Escribe una pregunta en lenguaje natural o pulsa /menu."

def _set_commands() -> None:
    commands = [{"command": name, "description": description[:256]} for name, description in COMMANDS]
    try:
        _api("setMyCommands", json={"commands": commands})
    except TelegramBotError:
        # Command registration is convenience only; transport failure must not hide polling.
        pass


def _handle_update(update: dict[str, Any], offset: int | None) -> int | None:
    update_id = update.get("update_id")
    next_offset = update_id + 1 if isinstance(update_id, int) else offset

    callback = update.get("callback_query")
    if isinstance(callback, dict):
        data = str(callback.get("data", ""))
        callback_id = callback.get("id")
        if callback_id:
            try:
                _answer_callback(str(callback_id))
            except TelegramBotError:
                pass
        message = callback.get("message") or {}
        chat_id = (message.get("chat") or {}).get("id")
        if chat_id is not None and data.startswith("cmd:"):
            _send(int(chat_id), render_command(data[4:]), _menu_markup())
        return next_offset

    message = update.get("message") or {}
    chat_id = (message.get("chat") or {}).get("id")
    text = str(message.get("text") or "").strip()
    if chat_id is not None and text:
        command = text.split()[0] if text.startswith("/") else _natural_query(text)
        if command:
            _send(int(chat_id), render_command(command), _menu_markup())
        else:
            _send(
                int(chat_id),
                "🟦 Puedo responder preguntas como:\n"
                "• ¿Qué está pasando ahora?\n"
                "• ¿Qué ha cambiado?\n"
                "• ¿Qué dicen los sondeos?\n"
                "• ¿Qué implica en escaños?\n"
                "• ¿Qué mayorías son posibles?\n"
                "• ¿Qué plazos importan?\n"
                "• ¿De dónde sale cada dato?",
                _menu_markup(),
            )
    return next_offset

def poll_once(offset: int | None = None) -> int | None:
    params: dict[str, Any] = {"timeout": 0, "allowed_updates": ["message", "callback_query"]}
    if offset is not None:
        params["offset"] = offset
    payload = _api("getUpdates", params=params)
    next_offset = offset
    for update in payload.get("result") or []:
        if isinstance(update, dict):
            next_offset = _handle_update(update, next_offset)
    return next_offset


def run_polling(*, poll_timeout: int = 25, sleep_seconds: float = 1.0) -> None:
    _token()
    try:
        _api("deleteWebhook", json={"drop_pending_updates": False})
    except TelegramBotError:
        pass
    _set_commands()
    offset = None
    while True:
        params: dict[str, Any] = {
            "timeout": poll_timeout,
            "allowed_updates": ["message", "callback_query"],
        }
        if offset is not None:
            params["offset"] = offset
        payload = _api("getUpdates", params=params)
        for update in payload.get("result") or []:
            if isinstance(update, dict):
                offset = _handle_update(update, offset)
        if sleep_seconds:
            time.sleep(sleep_seconds)


if __name__ == "__main__":
    run_polling()
