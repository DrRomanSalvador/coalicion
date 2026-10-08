"""Operational Telegram interface for the neutral COALICIÓN evidence pipeline."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

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
    ("menu", "Menú operativo"),
    ("briefing", "Briefing ejecutivo"),
    ("urgencias", "Urgencias y bloqueos"),
    ("cambios", "Cambios materiales"),
    ("encuestas", "Sondeos validados"),
    ("prediccion", "Proyección y límites"),
    ("territorio", "Cobertura territorial"),
    ("escenarios", "Escenarios materializados"),
    ("fuentes", "Salud de fuentes"),
    ("auditoria", "Auditoría y evidencia"),
    ("agenda", "Hitos materializados"),
    ("estado", "Estado del sistema"),
    ("radar", "Radar operativo"),
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


def _send(chat_id: int, text: str, markup: dict[str, Any] | None = None) -> None:
    payload: dict[str, Any] = {"chat_id": chat_id, "text": text[:MAX_MESSAGE]}
    if markup:
        payload["reply_markup"] = markup
    _api("sendMessage", json=payload)


def send_message(chat_id: int, text: str) -> None:
    _send(chat_id, text)


def _answer_callback(callback_id: str) -> None:
    _api("answerCallbackQuery", json={"callback_query_id": callback_id})


def _menu_markup() -> dict[str, Any]:
    return {
        "inline_keyboard": [
            [{"text": "🚨 Urgencias", "callback_data": "cmd:/urgencias"},
             {"text": "📋 Briefing", "callback_data": "cmd:/briefing"}],
            [{"text": "📈 Cambios", "callback_data": "cmd:/cambios"},
             {"text": "🗳 Encuestas", "callback_data": "cmd:/encuestas"}],
            [{"text": "🧮 Predicción", "callback_data": "cmd:/prediccion"},
             {"text": "🗺 Territorio", "callback_data": "cmd:/territorio"}],
            [{"text": "🧪 Escenarios", "callback_data": "cmd:/escenarios"},
             {"text": "🔎 Auditoría", "callback_data": "cmd:/auditoria"}],
            [{"text": "📡 Fuentes", "callback_data": "cmd:/fuentes"},
             {"text": "📅 Agenda", "callback_data": "cmd:/agenda"}],
            [{"text": "🟢 Estado", "callback_data": "cmd:/estado"},
             {"text": "📡 Radar", "callback_data": "cmd:/radar"}],
        ]
    }


def _help_text() -> str:
    return (
        "COALICIÓN · CONSOLA OPERATIVA NEUTRAL\n\n"
        "Usa el menú o estos comandos:\n\n"
        + "\n".join(f"/{name} — {description}" for name, description in COMMANDS)
        + "\n\nLa consola solo presenta evidencia materializada. "
          "Si falta un dato esencial, bloquea en lugar de inferirlo. "
          "No realiza persuasión, segmentación electoral ni recomendaciones políticas."
    )


def _urgencies_text() -> str:
    state = _safe_json(STATE)
    estimation = _safe_json(ESTIMATION)
    issues: list[str] = []
    if estimation.get("status") == "BLOCKED":
        issues.append("P1 · PREDICCIÓN BLOQUEADA: faltan observaciones territoriales explícitas.")
    if not _latest_polls():
        issues.append("P1 · No hay sondeos validados materializados.")
    failed = []
    for source in _sources():
        status = str(source.get("status", source.get("health", ""))).upper()
        if status in {"DOWN", "FAILED", "ERROR", "DEGRADED", "UNHEALTHY"}:
            failed.append(str(source.get("id", source.get("source_id", source.get("name", "?")))))
    if failed:
        issues.append("P1 · Fuentes con incidencia: " + ", ".join(failed[:10]))
    warnings = _list_records(state.get("warnings"))
    if warnings:
        issues.append("P2 · Advertencias persistentes: " + "; ".join(str(x.get("message", x)) for x in warnings[:3]))
    if not issues:
        issues.append("P4 · Sin bloqueos críticos materializados.")
    return "🚨 URGENCIAS\n\n" + "\n".join(f"• {x}" for x in issues) + (
        "\n\nHechos y bloqueos, no recomendaciones políticas."
    )


def _polls_text() -> str:
    polls = _latest_polls()
    if not polls:
        return "🗳 ENCUESTAS\nNo hay observaciones validadas materializadas."
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
        lines.append("⚠️ Escaños bloqueados: no existe observación territorial verificable.")
    return "\n".join(lines)


def _prediction_text() -> str:
    estimation = _safe_json(ESTIMATION)
    snapshot = _safe_json(SNAPSHOT)
    if estimation.get("status") == "BLOCKED":
        return (
            "🧮 PREDICCIÓN · BLOQUEADA\n\n"
            f"Motivo: {estimation.get('reason', 'sin motivo materializado')}\n"
            f"Sondeos nacionales: {estimation.get('national_poll_count', 0)}\n"
            f"Observaciones territoriales: {estimation.get('territorial_poll_count', 0)}\n"
            "No se convierte una encuesta nacional en escaños por inferencia."
        )
    projection = snapshot.get("projection")
    if not isinstance(projection, dict):
        return "🧮 PREDICCIÓN · BLOQUEADA\nNo existe snapshot territorial materializado."
    seats = projection.get("national_seats") or projection.get("party")
    if not isinstance(seats, dict) or not seats:
        return "🧮 PREDICCIÓN · BLOQUEADA\nEl snapshot no contiene escaños verificables."
    rows = []
    for party, value in seats.items():
        try:
            rows.append((str(party), int(value)))
        except (TypeError, ValueError):
            continue
    rows.sort(key=lambda x: (-x[1], x[0]))
    return "🧮 PROYECCIÓN OBSERVADA\n\n" + "\n".join(f"{p}: {s}" for p, s in rows)


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
           "🔴 BLOQUEADO: no hay entrada territorial explícita suficiente. "
           "No se fabrica distribución provincial ni se transforma nacional→territorial.")
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
        return "🧪 ESCENARIOS\nNo hay escenarios materializados en artifacts/."
    lines = ["🧪 ESCENARIOS MATERIALIZADOS", ""]
    for path in files:
        data = _safe_json(path)
        if not data:
            lines.append(f"• {path.name}: inválido o ilegible → BLOQUEADO")
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
        return "📡 FUENTES\nNo hay estado de fuentes materializado."
    lines = ["📡 FUENTES · SALUD MATERIALIZADA", ""]
    for source in sources[:35]:
        sid = source.get("id", source.get("source_id", source.get("name", "?")))
        status = source.get("status", source.get("health", "UNKNOWN"))
        error = source.get("error") or source.get("last_error")
        line = f"{sid}: {status}"
        if error:
            line += f" · {str(error)[:160]}"
        lines.append(line)
    return "\n".join(lines)


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
        f"Estado OOS: {oos.get('status', 'n/d')}",
        f"Elecciones OOS registradas: {oos.get('elections', 'n/d')}",
        f"Observaciones OOS: {oos.get('poll_observations', 'n/d')}",
        f"Predicción actual: {estimation.get('status', 'n/d')}",
        "",
        "Bloqueos:",
    ]
    lines.extend(f"• {x}" for x in blocked[:8]) if blocked else lines.append("• ninguno materializado")
    lines.append("")
    lines.append("Advertencias:")
    lines.extend(f"• {x}" for x in warnings[:5]) if warnings else lines.append("• ninguna materializada")
    lines.append("")
    lines.append("No se presenta certificación oficial mientras existan bloqueos de evidencia.")
    return "\n".join(lines)


def _agenda_text() -> str:
    radar = _safe_json(ESTIMATION).get("radar") or {}
    alerts = _list_records(radar.get("alerts"))
    if not alerts:
        return "📅 AGENDA\nNo hay hitos materializados en el radar."
    lines = ["📅 AGENDA · HITOS MATERIALIZADOS", ""]
    for alert in alerts[:12]:
        facts = alert.get("facts") or {}
        date = facts.get("date", "n/d")
        days = facts.get("days_remaining")
        suffix = f" · {days} días" if days is not None else ""
        lines.append(f"• {date}{suffix} · {alert.get('title', alert.get('code', 'hito'))}")
    return "\n".join(lines)


def _radar_text() -> str:
    radar = _safe_json(ESTIMATION).get("radar") or {}
    alerts = _list_records(radar.get("alerts"))
    if not radar:
        return "📡 RADAR\nSin radar materializado."
    lines = [
        f"📡 RADAR · {radar.get('as_of', 'n/d')} · {radar.get('status', 'UNKNOWN')}",
        f"Alertas materializadas: {len(alerts)}",
        "",
    ]
    for alert in alerts[:10]:
        lines.append(
            f"[{alert.get('priority', 'P4')}] {alert.get('title', '')} · "
            f"{alert.get('reason', '')}"
        )
    if _safe_json(ESTIMATION).get("status") == "BLOCKED":
        lines.extend(["", "🔴 BLOQUEO PREDICTIVO", "No hay observación territorial explícita suficiente."])
    return "\n".join(lines)


def _changes_text() -> str:
    polls = _latest_polls()
    if len(polls) < 2:
        return "📈 CAMBIOS\nSe necesitan al menos dos observaciones validadas."
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
        f"Predicción: {estimation.get('status', 'SIN_EJECUCIÓN')}\n"
        "Metodología: NOT_PROMOTED hasta OOS + calibración reales\n"
        "Modo: fail-closed · sin datos sintéticos · sin inferencia nacional→territorial"
    )


def _briefing_text() -> str:
    return (
        "📋 BRIEFING OPERATIVO\n\n"
        + _urgencies_text().replace("🚨 URGENCIAS\n\n", "🚨 URGENCIAS\n")
        + "\n\n"
        + _changes_text().replace("📈 CAMBIOS MATERIALES\n\n", "📈 CAMBIOS\n")
        + "\n\n"
        + _status_text().replace("🟢 ESTADO COALICIÓN\n\n", "🟢 ESTADO\n")
        + "\n\n"
        + "🔎 AUDITORÍA\n"
        + f"Predicción: {_safe_json(ESTIMATION).get('status', 'n/d')} · "
          "la certificación estricta permanece separada del estado operativo."
    )


def render_command(command: str) -> str:
    command = command.split("@", 1)[0].strip().lower()
    aliases = {"/help": "/ayuda", "/start": "/menu"}
    command = aliases.get(command, command)
    renderers = {
        "/menu": _help_text,
        "/ayuda": _help_text,
        "/briefing": _briefing_text,
        "/urgencias": _urgencies_text,
        "/cambios": _changes_text,
        "/encuestas": _polls_text,
        "/prediccion": _prediction_text,
        "/territorio": _territory_text,
        "/escenarios": _scenarios_text,
        "/fuentes": _sources_text,
        "/auditoria": _audit_text,
        "/agenda": _agenda_text,
        "/estado": _status_text,
        "/radar": _radar_text,
    }
    renderer = renderers.get(command)
    return renderer() if renderer else "Comando no reconocido. Usa /menu."


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
            command = data[4:]
            _send(int(chat_id), render_command(command), _menu_markup())
        return next_offset

    message = update.get("message") or {}
    chat_id = (message.get("chat") or {}).get("id")
    text = str(message.get("text") or "").strip()
    if chat_id is not None and text.startswith("/"):
        command = text.split()[0]
        _send(int(chat_id), render_command(command), _menu_markup())
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
