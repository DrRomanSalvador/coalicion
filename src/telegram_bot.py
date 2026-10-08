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
    ("alertas", "Configurar alertas"),
    ("hechos", "Solo hechos"),
    ("exportar", "Exportar datos"),
    ("comparar", "Comparar observaciones"),
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
        "La cifra actual de escaños requiere evidencia provincial explícita y una distribución territorial explícita. "
        "El sistema no convierte automáticamente porcentajes nacionales en reparto territorial."
    )



# --- Telegram product layer: preferences, security, alerts, evidence, exports ---

ALERT_CATEGORIES = {
    "nueva_encuesta": "🔴 Nueva encuesta",
    "modificacion_encuesta": "🟠 Modificación de encuesta",
    "cambio_territorial": "🟣 Cambio territorial",
    "nuevo_dato_oficial": "🟡 Nuevo dato oficial",
    "cambio_plazo_legal": "⚖️ Cambio/plazo legal",
    "cambio_escenario": "📊 Cambio de escenario",
    "cambio_evidencia": "🔎 Cambio de evidencia",
    "recuperacion_fuente": "🟢 Recuperación de fuente",
}
ALERT_FREQUENCIES = {"immediate": "inmediata", "hourly": "horaria", "daily": "diaria"}
TELEGRAM_CONFIG = ROOT / "artifacts/telegram_config.json"
AUDIT_LOG = ROOT / "artifacts/telegram_audit.jsonl"
RATE_WINDOW = 60.0
RATE_LIMIT_PRIVATE = 10
RATE_LIMIT_GROUP = 100
_RATE: dict[str, list[float]] = {}


def _config() -> dict[str, Any]:
    value = _safe_json(TELEGRAM_CONFIG)
    if not isinstance(value.get("users"), dict):
        value["users"] = {}
    if not isinstance(value.get("chats"), dict):
        value["chats"] = {}
    return value


def _save_config(value: dict[str, Any]) -> None:
    try:
        TELEGRAM_CONFIG.parent.mkdir(parents=True, exist_ok=True)
        tmp = TELEGRAM_CONFIG.with_suffix(".tmp")
        tmp.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        tmp.replace(TELEGRAM_CONFIG)
    except OSError:
        pass


def _chat_id(update: dict[str, Any]) -> str:
    callback = update.get("callback_query") or {}
    message = callback.get("message") or {}
    chat = message.get("chat") or update.get("message", {}).get("chat") or {}
    return str(chat.get("id", ""))


def _user_id(update: dict[str, Any]) -> str:
    callback = update.get("callback_query") or {}
    user = callback.get("from") or update.get("message", {}).get("from") or {}
    return str(user.get("id", ""))


def _chat_allowed(chat_id: str) -> bool:
    raw = os.environ.get("TELEGRAM_ALLOWED_CHATS", "").strip()
    if not raw:
        return True
    return chat_id in {x.strip() for x in raw.split(",") if x.strip()}


def _admin_allowed(update: dict[str, Any]) -> bool:
    admins = {x.strip() for x in os.environ.get("TELEGRAM_ADMIN_IDS", "").split(",") if x.strip()}
    return bool(admins) and _user_id(update) in admins


def _rate_allowed(update: dict[str, Any]) -> bool:
    uid = _user_id(update) or _chat_id(update)
    now = time.time()
    values = [x for x in _RATE.get(uid, []) if now - x < RATE_WINDOW]
    message = update.get("message") or (update.get("callback_query") or {}).get("message") or {}
    chat_type = str((message.get("chat") or {}).get("type", "private"))
    limit = RATE_LIMIT_GROUP if chat_type in {"group", "supergroup"} else RATE_LIMIT_PRIVATE
    if len(values) >= limit:
        _RATE[uid] = values
        return False
    values.append(now)
    _RATE[uid] = values
    return True


def _audit(update: dict[str, Any], command: str, query: str = "", response: str = "") -> None:
    import hashlib
    from datetime import datetime, timezone
    record = {
        "user_id": _user_id(update), "chat_id": _chat_id(update), "command": command,
        "query": query[:500],
        "response_hash": hashlib.sha256(response.encode("utf-8")).hexdigest(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with AUDIT_LOG.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    except OSError:
        pass


def _preferences(update: dict[str, Any]) -> dict[str, Any]:
    cfg = _config()
    key = _chat_id(update) or _user_id(update)
    prefs = cfg["chats"].get(key) or cfg["users"].get(_user_id(update)) or {}
    categories = prefs.get("categories")
    if not isinstance(categories, dict):
        categories = {k: True for k in ALERT_CATEGORIES}
    return {
        "categories": {k: bool(categories.get(k, True)) for k in ALERT_CATEGORIES},
        "frequency": str(prefs.get("frequency", "immediate")),
        "quiet_start": str(prefs.get("quiet_start", "22:00")),
        "quiet_end": str(prefs.get("quiet_end", "08:00")),
        "threshold": float(prefs.get("threshold", 0.0) or 0.0),
    }


def _set_preferences(update: dict[str, Any], **changes: Any) -> None:
    cfg = _config()
    key = _chat_id(update) or _user_id(update)
    prefs = _preferences(update)
    prefs.update(changes)
    cfg["chats"][key] = prefs
    _save_config(cfg)


def _alerts_markup(update: dict[str, Any]) -> dict[str, Any]:
    prefs = _preferences(update)
    rows = []
    for category, label in ALERT_CATEGORIES.items():
        mark = "✅" if prefs["categories"].get(category, True) else "⬜"
        rows.append([{"text": f"{mark} {label}", "callback_data": f"alert:toggle:{category}"}])
    rows.extend([
        [{"text": f"⏱ Frecuencia: {ALERT_FREQUENCIES.get(prefs['frequency'], prefs['frequency'])}", "callback_data": "alert:frequency"}],
        [{"text": f"🌙 Silencio {prefs['quiet_start']}–{prefs['quiet_end']}", "callback_data": "alert:quiet"}],
        [{"text": f"📏 Umbral: {prefs['threshold']:.1f} pp", "callback_data": "alert:threshold"}],
        [{"text": "🏠 Inicio", "callback_data": "home"}],
    ])
    return {"inline_keyboard": rows}


def _alerts_text(update: dict[str, Any]) -> str:
    prefs = _preferences(update)
    lines = [
        "🔔 ALERTAS · CONFIGURACIÓN", "",
        f"Frecuencia: {ALERT_FREQUENCIES.get(prefs['frequency'], prefs['frequency'])}",
        f"Silencio: {prefs['quiet_start']}–{prefs['quiet_end']}",
        f"Umbral: {prefs['threshold']:.1f} pp", "", "Categorías:"
    ]
    for category, label in ALERT_CATEGORIES.items():
        lines.append(("• ✅ " if prefs["categories"].get(category, True) else "• ⬜ ") + label)
    lines.append("\nPulsa una categoría para activarla o desactivarla.")
    return "\n".join(lines)


def _poll_card(index: int) -> str:
    polls = _latest_polls()
    if not polls or index < 0 or index >= len(polls):
        return "🗳 FICHA DE ENCUESTA\n\nNo hay una observación validada disponible."
    poll = polls[index]
    parties = poll.get("parties") if isinstance(poll.get("parties"), dict) else {}
    parsed = []
    for party, value in parties.items():
        try:
            parsed.append((str(party), float(value)))
        except (TypeError, ValueError):
            pass
    parsed.sort(key=lambda x: (-x[1], x[0]))
    lines = [
        "🗳 FICHA DE ENCUESTA", "",
        f"Publicación: {poll.get('publication_date', 'n/d')}",
        f"Campo: {poll.get('field_date', poll.get('fieldwork_date', 'n/d'))}",
        f"Encuestadora/fuente: {poll.get('pollster', poll.get('source_id', 'n/d'))}",
        f"Muestra: {poll.get('sample_size', poll.get('sample', 'n/d'))}",
        f"Metodología: {poll.get('methodology', 'n/d')}", "", "Estimaciones:"
    ]
    lines.extend(f"• {p}: {v:.1f}%" for p, v in parsed[:12])
    return "\n".join(lines)


def _poll_card_markup(index: int) -> dict[str, Any]:
    polls = _latest_polls()
    row = []
    if index > 0:
        row.append({"text": "← Anterior", "callback_data": f"evidence:poll:{index-1}"})
    if index + 1 < len(polls):
        row.append({"text": "Siguiente →", "callback_data": f"evidence:poll:{index+1}"})
    rows = [row] if row else []
    rows.extend([
        [{"text": "🔎 ¿De dónde sale?", "callback_data": f"evidence:detail:{index}"}],
        [{"text": "📈 Cambios", "callback_data": "cmd:/cambios"}, {"text": "🏠 Inicio", "callback_data": "home"}],
    ])
    return {"inline_keyboard": rows}


def _evidence_detail(index: int) -> str:
    polls = _latest_polls()
    if not polls or index < 0 or index >= len(polls):
        return "🔎 EVIDENCIA\n\nNo hay evidencia materializada para mostrar."
    poll = polls[index]
    fields = [
        ("Fuente/URL", poll.get("source_url") or poll.get("url") or poll.get("source_id") or poll.get("source")),
        ("Publicación", poll.get("publication_date")),
        ("Campo", poll.get("field_date") or poll.get("fieldwork_date")),
        ("Captura", poll.get("capture_date") or poll.get("retrieved_at")),
        ("Hash", poll.get("sha256") or poll.get("hash")),
        ("Materialización", poll.get("materialization") or poll.get("artifact")),
        ("Transformación", poll.get("transformation")),
        ("Verificación", poll.get("verification_level") or poll.get("status")),
        ("Advertencias", poll.get("warnings") or "Ninguna registrada"),
    ]
    lines = ["🔎 EVIDENCIA · FICHA", ""]
    for label, value in fields:
        lines.append(f"{label}: {value if value not in (None, '') else 'n/d'}")
    lines.append("\nNo se completan campos ausentes por inferencia.")
    return "\n".join(lines)


def _scenario_markup() -> dict[str, Any]:
    return {"inline_keyboard": [
        [{"text": "Base", "callback_data": "scenario:central"}, {"text": "Optimista", "callback_data": "scenario:optimista"}, {"text": "Pesimista", "callback_data": "scenario:pesimista"}],
        [{"text": "🪑 Escaños", "callback_data": "scenario:view:seats"}, {"text": "📐 Incertidumbre", "callback_data": "scenario:view:uncertainty"}],
        [{"text": "🗺 Territorio", "callback_data": "scenario:view:territory"}, {"text": "🔎 Evidencia", "callback_data": "scenario:view:evidence"}],
        [{"text": "🏠 Inicio", "callback_data": "home"}],
    ]}


def _scenario_text(name: str = "central") -> str:
    data = _safe_json(SCENARIO_DIR / f"scenario_{name}.json")
    if not data:
        return "🧪 ESCENARIO\n\nNo existe un escenario materializado de este tipo."
    return f"🧪 ESCENARIO · {name.upper()}\n\nEstado: {data.get('status', 'materializado')}\nSchema: {data.get('schema', 'n/d')}\n\nSolo se muestran cifras materializadas."


def _territory_markup() -> dict[str, Any]:
    return {"inline_keyboard": [
        [{"text": "🇪🇸 España", "callback_data": "territory:ES"}],
        [{"text": "🔎 Evidencia", "callback_data": "cmd:/evidencia"}, {"text": "← Atrás", "callback_data": "back"}],
    ]}


def _export_payload(kind: str) -> tuple[bytes, str, str]:
    if kind == "polls":
        data = _latest_polls()
        return json.dumps(data, ensure_ascii=False, indent=2).encode(), "coalicion_encuestas.json", "application/json"
    if kind == "evidence":
        data = [{"index": i, "poll": p} for i, p in enumerate(_latest_polls()[:20])]
        return json.dumps(data, ensure_ascii=False, indent=2).encode(), "coalicion_evidencia.json", "application/json"
    if kind == "changes":
        return _changes_text().encode(), "coalicion_cambios.txt", "text/plain"
    return json.dumps({"briefing": _briefing_text()}, ensure_ascii=False, indent=2).encode(), "coalicion_briefing.json", "application/json"


def _send_document(chat_id: int, data: bytes, filename: str, content_type: str) -> None:
    _api("sendDocument", files={"document": (filename, data, content_type)}, data={"chat_id": str(chat_id)})


def _facts_text() -> str:
    polls = _latest_polls()
    sources = _sources()
    lines = [
        "📚 SOLO HECHOS", "", "Elección: 29/11/2026", "Cámara: 350 escaños",
        "Circunscripciones: 52", f"Sondeos validados: {len(polls)}", f"Fuentes registradas: {len(sources)}",
    ]
    if polls:
        p = polls[0]
        lines += ["", f"Observación más reciente: {p.get('publication_date', 'n/d')}",
                  f"Fuente/encuestadora: {p.get('pollster', p.get('source_id', 'n/d'))}"]
        parties = p.get("parties") if isinstance(p.get("parties"), dict) else {}
        for party, value in list(parties.items())[:12]:
            try:
                lines.append(f"{party}: {float(value):.1f}%")
            except (TypeError, ValueError):
                pass
    return "\n".join(lines)


def _digest_text() -> str:
    briefing = build_briefing(as_of=date.today(), polls=_latest_polls(), sources=_sources(), observations=_observations(), horizon_days=31)
    lines = ["🧭 PARTE ELECTORAL · 08:00", ""]
    for item in briefing[:6]:
        lines += [f"• {item['title']}", f"  {item['detail']}"]
    if len(lines) == 2:
        lines.append("• Sin novedades operativas materializadas.")
    lines += ["", "Datos fechados y trazables. Sin recomendación política."]
    return "\n".join(lines)


def _configure_bot_ui() -> None:
    _set_commands()
    webapp = os.environ.get("TELEGRAM_WEBAPP_URL", "").strip()
    if webapp:
        try:
            _api("setChatMenuButton", json={"menu_button": {"type": "web_app", "text": "Panel", "web_app": {"url": webapp}}})
        except TelegramBotError:
            pass

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
        (("/alertas", "alertas", "avisos", "notificaciones"), "/alertas"),
        (("/hechos", "solo hechos", "hechos", "sin interpretacion"), "/hechos"),
        (("/exportar", "exporta", "exportar", "csv", "json", "informe"), "/exportar"),
        (("/comparar", "compara", "comparame", "comparación", "comparacion", "ultimas 5"), "/comparar"),
        (("ponme al dia", "ponme al día"), "/briefing"),
    ]
    for needles, command in rules:
        if any(needle in normalized for needle in needles):
            return command
    return None


USER_STATE = ROOT / "artifacts/telegram_user_state.json"
MAX_STATE_USERS = 10000


def _state_key(update: dict[str, Any]) -> str:
    callback = update.get("callback_query") or {}
    message = callback.get("message") or {}
    user = callback.get("from") or {}
    chat_id = (message.get("chat") or {}).get("id")
    user_id = user.get("id")
    return str(user_id if user_id is not None else chat_id if chat_id is not None else "")


def _load_user_state() -> dict[str, Any]:
    value = _safe_json(USER_STATE)
    users = value.get("users")
    return users if isinstance(users, dict) else {}


def _save_user_state(users: dict[str, Any]) -> None:
    try:
        USER_STATE.parent.mkdir(parents=True, exist_ok=True)
        trimmed = dict(list(users.items())[-MAX_STATE_USERS:])
        tmp = USER_STATE.with_suffix(".tmp")
        tmp.write_text(json.dumps({"users": trimmed}, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        tmp.replace(USER_STATE)
    except OSError:
        # Navigation remains functional if persistence is temporarily unavailable.
        pass


def _get_user_navigation(key: str) -> dict[str, Any]:
    users = _load_user_state()
    value = users.get(key)
    if not isinstance(value, dict):
        return {"current": "/briefing", "stack": []}
    return {
        "current": str(value.get("current", "/briefing")),
        "stack": [str(x) for x in value.get("stack", []) if isinstance(x, str)][-20:],
    }


def _set_user_navigation(key: str, current: str, *, previous: str | None = None) -> None:
    if not key:
        return
    users = _load_user_state()
    state = _get_user_navigation(key)
    stack = list(state["stack"])
    if previous and previous != current:
        stack.append(previous)
    users[key] = {"current": current, "stack": stack[-20:]}
    _save_user_state(users)


def _navigation_markup(command: str) -> dict[str, Any]:
    command = command.split("@", 1)[0].strip().lower()
    if command in {"/briefing", "/hoy"}:
        return {
            "inline_keyboard": [
                [{"text": "🔄 Actualizar", "callback_data": f"refresh:{command}"},
                 {"text": "🧭 Inicio", "callback_data": "home"}],
                [{"text": "📈 Cambios", "callback_data": "cmd:/cambios"},
                 {"text": "🗳 Sondeos", "callback_data": "cmd:/encuestas"}],
                [{"text": "📅 Plazos", "callback_data": "cmd:/calendario"},
                 {"text": "🔎 Evidencia", "callback_data": "cmd:/evidencia"}],
            ]
        }
    return {
        "inline_keyboard": [
            [{"text": "← Atrás", "callback_data": "back"},
             {"text": "🏠 Inicio", "callback_data": "home"},
             {"text": "🔄 Actualizar", "callback_data": f"refresh:{command}"}],
        ]
    }


def _edit(chat_id: int, message_id: int, text: str, markup: dict[str, Any] | None = None) -> None:
    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": _public_text(text),
    }
    if markup is not None:
        payload["reply_markup"] = markup
    _api("editMessageText", json=payload)


def _callback_command(data: str) -> str | None:
    if data.startswith("cmd:"):
        return data[4:]
    if data.startswith("refresh:"):
        return data[8:]
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
           "ℹ️ Cobertura territorial actual limitada: los escaños requieren evidencia provincial explícita y una distribución territorial explícita. "
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
        "/alertas": lambda: "🔔 ALERTAS · CONFIGURACIÓN\n\nAbre /alertas para gestionar categorías, frecuencia, silencio y umbral.",
        "/hechos": _facts_text,
        "/exportar": lambda: "📤 EXPORTACIÓN\n\nElige CSV/JSON desde las fichas disponibles.",
        "/comparar": _changes_text,
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



def _alert_state() -> dict[str, Any]:
    return _safe_json(ROOT / "artifacts/telegram_alert_state.json")


def _save_alert_state(value: dict[str, Any]) -> None:
    path = ROOT / "artifacts/telegram_alert_state.json"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        tmp.replace(path)
    except OSError:
        pass


def _alert_candidates() -> list[dict[str, Any]]:
    candidates = []
    polls = _latest_polls()
    if polls:
        p = polls[0]
        key = f"poll:{p.get('publication_date')}:{p.get('pollster', p.get('source_id', ''))}"
        candidates.append({
            "key": key, "category": "nueva_encuesta",
            "title": "Nueva observación de sondeo",
            "detail": f"{p.get('publication_date', 'n/d')} · {p.get('pollster', p.get('source_id', 'fuente no indicada'))}",
        })
    for item in build_briefing(as_of=date.today(), polls=polls, sources=_sources(),
                               observations=_observations(), horizon_days=31)[:4]:
        candidates.append({
            "key": f"briefing:{item.get('code', item.get('title'))}:{item.get('due', '')}",
            "category": "cambio_plazo_legal" if item.get("code", "").startswith("LEGAL") else "cambio_evidencia",
            "title": item.get("title", "Novedad"),
            "detail": item.get("detail", ""),
        })
    return candidates


def _in_quiet(prefs: dict[str, Any]) -> bool:
    from datetime import datetime
    now = datetime.now().strftime("%H:%M")
    start, end = prefs["quiet_start"], prefs["quiet_end"]
    if start == end:
        return False
    if start < end:
        return start <= now < end
    return now >= start or now < end


def _send_alerts_to_chat(chat_id: int, *, frequency: str = "immediate") -> None:
    cfg = _config()
    prefs = cfg.get("chats", {}).get(str(chat_id), {})
    if not isinstance(prefs, dict):
        prefs = {"categories": {k: True for k in ALERT_CATEGORIES}, "frequency": "immediate"}
    categories = prefs.get("categories") if isinstance(prefs.get("categories"), dict) else {}
    if str(prefs.get("frequency", "immediate")) != frequency or _in_quiet(_preferences({"message": {"chat": {"id": chat_id}, "from": {"id": chat_id}}})):
        return
    state = _alert_state()
    sent = state.get(str(chat_id), [])
    if not isinstance(sent, list):
        sent = []
    pending = [x for x in _alert_candidates()
               if categories.get(x["category"], True) and x["key"] not in sent]
    if not pending:
        return
    pending = pending[:10]
    lines = ["🔔 COALICIÓN · NOVEDADES", ""]
    for item in pending:
        lines += [f"• {ALERT_CATEGORIES[item['category']]} · {item['title']}", f"  {item['detail']}"]
    lines.append("\n🔎 Datos fechados y trazables.")
    _send(chat_id, "\n".join(lines), _menu_markup())
    state[str(chat_id)] = (sent + [x["key"] for x in pending])[-100:]
    _save_alert_state(state)


def _maybe_send_scheduled_digest() -> None:
    from datetime import datetime
    now = datetime.now()
    if now.minute > 5:
        return
    cfg = _config()
    if now.hour not in {8}:
        return
    stamp = now.strftime("%Y-%m-%d")
    marker = ROOT / "artifacts/telegram_digest_state.json"
    state = _safe_json(marker)
    if state.get("last") == stamp:
        return
    for chat_id, prefs in (cfg.get("chats") or {}).items():
        if isinstance(prefs, dict) and prefs.get("frequency") == "daily":
            try:
                _send(int(chat_id), _digest_text(), _menu_markup())
            except (TelegramBotError, ValueError):
                continue
    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(json.dumps({"last": stamp}), encoding="utf-8")
    except OSError:
        pass


def _inline_query(update: dict[str, Any]) -> None:
    query = str((update.get("inline_query") or {}).get("query") or "").strip()
    inline_id = str((update.get("inline_query") or {}).get("id") or "")
    if not inline_id:
        return
    command = _natural_query(query) or "/briefing"
    text = render_command(command)
    results = [{
        "type": "article",
        "id": "briefing",
        "title": "COALICIÓN · Sala de Situación",
        "description": "Datos, cambios, plazos y evidencia verificable",
        "input_message_content": {"message_text": _public_text(text)},
        "reply_markup": {"inline_keyboard": [[
            {"text": "🧭 Abrir Sala", "callback_data": "cmd:/briefing"}
        ]]},
    }]
    _api("answerInlineQuery", json={"inline_query_id": inline_id, "results": results, "cache_time": 0, "is_personal": True})


def _handle_update(update: dict[str, Any], offset: int | None) -> int | None:
    update_id = update.get("update_id")
    next_offset = update_id + 1 if isinstance(update_id, int) else offset

    if "inline_query" in update:
        if _rate_allowed(update):
            try:
                _inline_query(update)
            except TelegramBotError:
                pass
        return next_offset

    chat_id = _chat_id(update)
    if chat_id and not _chat_allowed(chat_id):
        callback = update.get("callback_query")
        if callback and callback.get("id"):
            _answer_callback(str(callback["id"]))
        elif (update.get("message") or {}).get("chat"):
            _send(int(chat_id), "🛡 Este chat no está autorizado para utilizar COALICIÓN.")
        return next_offset

    if not _rate_allowed(update):
        if (update.get("message") or {}).get("chat"):
            _send(int(chat_id), "⏳ Límite temporal alcanzado. Inténtalo de nuevo en un momento.")
        return next_offset

    callback = update.get("callback_query")
    if isinstance(callback, dict):
        data = str(callback.get("data", ""))
        if callback.get("id"):
            _answer_callback(str(callback["id"]))
        message = callback.get("message") or {}
        message_id = message.get("message_id")
        if chat_id and isinstance(message_id, int):
            key = _state_key(update)
            state = _get_user_navigation(key)
            current = state["current"]
            target = None
            markup = None
            text = None
            if data == "home":
                target = "/briefing"
            elif data == "back":
                stack = list(state["stack"])
                target = stack.pop() if stack else "/briefing"
                users = _load_user_state()
                users[key] = {"current": target, "stack": stack[-20:]}
                _save_user_state(users)
            elif data.startswith("alert:toggle:"):
                category = data.rsplit(":", 1)[-1]
                prefs = _preferences(update)
                cats = dict(prefs["categories"])
                if category in cats:
                    cats[category] = not cats[category]
                    _set_preferences(update, categories=cats)
                text, markup = _alerts_text(update), _alerts_markup(update)
            elif data == "alert:frequency":
                order = ["immediate", "hourly", "daily"]
                current_freq = _preferences(update)["frequency"]
                nxt = order[(order.index(current_freq) + 1) % len(order)] if current_freq in order else "immediate"
                _set_preferences(update, frequency=nxt)
                text, markup = _alerts_text(update), _alerts_markup(update)
            elif data == "alert:quiet":
                prefs = _preferences(update)
                off = prefs["quiet_start"] == prefs["quiet_end"]
                _set_preferences(update, quiet_start="22:00" if off else "00:00",
                                 quiet_end="08:00" if off else "00:00")
                text, markup = _alerts_text(update), _alerts_markup(update)
            elif data == "alert:threshold":
                values = [0.0, 0.5, 1.0, 2.0]
                old = _preferences(update)["threshold"]
                idx = values.index(old) if old in values else 0
                _set_preferences(update, threshold=values[(idx + 1) % len(values)])
                text, markup = _alerts_text(update), _alerts_markup(update)
            elif data.startswith("evidence:poll:"):
                index = int(data.rsplit(":", 1)[-1])
                text, markup = _poll_card(index), _poll_card_markup(index)
            elif data.startswith("evidence:detail:"):
                index = int(data.rsplit(":", 1)[-1])
                text, markup = _evidence_detail(index), {"inline_keyboard": [[
                    {"text": "← Ficha", "callback_data": f"evidence:poll:{index}"},
                    {"text": "🏠 Inicio", "callback_data": "home"},
                ]]}
            elif data.startswith("scenario:") and data.count(":") == 1:
                name = data.split(":", 1)[1]
                text, markup = _scenario_text(name), _scenario_markup()
            elif data.startswith("scenario:view:"):
                view = data.split(":", 2)[2]
                text = _scenario_text("central") + f"\n\nVista solicitada: {view}."
                markup = _scenario_markup()
            elif data.startswith("territory:"):
                text = _territory_text()
                markup = _territory_markup()
            elif data.startswith("export:"):
                kind = data.split(":")[-1]
                _export_text(int(chat_id), "polls" if kind == "polls" else kind)
                text, markup = "📤 EXPORTACIÓN\n\nArchivo enviado al chat.", _menu_markup()
            else:
                target = _callback_command(data)
            if target:
                target = target.split("@", 1)[0].strip().lower()
                _set_user_navigation(key, target, previous=current)
                text = render_command(target)
                markup = _navigation_markup(target)
            if text is not None:
                try:
                    _edit(int(chat_id), int(message_id), text, markup)
                except TelegramBotError:
                    _send(int(chat_id), text, markup)
                _audit(update, "callback", data, text)
        return next_offset

    message = update.get("message") or {}
    text_in = str(message.get("text") or "").strip()
    if not text_in or not chat_id:
        return next_offset
    chat_type = str((message.get("chat") or {}).get("type", "private"))
    bot_username = os.environ.get("TELEGRAM_BOT_USERNAME", "").strip().lstrip("@").lower()
    if chat_type in {"group", "supergroup"} and not text_in.startswith("/"):
        if not bot_username or f"@{bot_username}" not in text_in.lower():
            return next_offset
        text_in = re.sub(rf"@{re.escape(bot_username)}", "", text_in, flags=re.IGNORECASE).strip()

    command = text_in.split()[0] if text_in.startswith("/") else _natural_query(text_in)
    key = str(_user_id(update) or chat_id)
    if command:
        command = command.split("@", 1)[0].strip().lower()
        if command == "/alertas":
            response, markup = _alerts_text(update), _alerts_markup(update)
        elif command == "/hechos":
            response, markup = _facts_text(), _navigation_markup("/hechos")
        elif command == "/exportar":
            response, markup = "📤 EXPORTACIÓN\n\nSelecciona el conjunto de datos:", {
                "inline_keyboard": [
                    [{"text": "🗳 Sondeos JSON", "callback_data": "export:json:polls"}],
                    [{"text": "🔎 Evidencia JSON", "callback_data": "export:json:evidence"}],
                    [{"text": "📈 Cambios", "callback_data": "export:txt:changes"}],
                    [{"text": "🏠 Inicio", "callback_data": "home"}],
                ],
            }
        elif command == "/comparar":
            response, markup = _changes_text(), {
                "inline_keyboard": [
                    [{"text": "🗳 Ver ficha actual", "callback_data": "evidence:poll:0"}],
                    [{"text": "📤 Exportar cambios", "callback_data": "export:txt:changes"}],
                    [{"text": "🏠 Inicio", "callback_data": "home"}],
                ],
            }
        elif command == "/escenarios":
            response, markup = _scenarios_text(), _scenario_markup()
        elif command == "/territorio":
            response, markup = _territory_text(), _territory_markup()
        else:
            response, markup = render_command(command), _navigation_markup(command)
        _set_user_navigation(key, command, previous=_get_user_navigation(key)["current"])
        _send(int(chat_id), response, markup)
        _audit(update, command, text_in, response)
        if _preferences(update)["frequency"] == "immediate":
            try:
                _send_alerts_to_chat(int(chat_id), frequency="immediate")
            except TelegramBotError:
                pass
    else:
        response = (
            "🟦 No he identificado la pregunta.\n\n"
            "Prueba: «ponme al día», «qué ha cambiado», «qué dicen los sondeos», "
            "«qué vence esta semana» o «de dónde sale este dato»."
        )
        _send(int(chat_id), response, _menu_markup())
        _audit(update, "natural_language_fallback", text_in, response)
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
    _configure_bot_ui()
    offset = None
    while True:
        params: dict[str, Any] = {
            "timeout": poll_timeout,
            "allowed_updates": ["message", "callback_query", "inline_query"],
        }
        if offset is not None:
            params["offset"] = offset
        payload = _api("getUpdates", params=params)
        for update in payload.get("result") or []:
            if isinstance(update, dict):
                offset = _handle_update(update, offset)
        _maybe_send_scheduled_digest()
        if sleep_seconds:
            time.sleep(sleep_seconds)


if __name__ == "__main__":
    run_polling()
