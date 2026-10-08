import json

from src import telegram_bot


def test_start_is_operational_menu():
    text = telegram_bot.render_command("/start")
    assert "PANEL DE HOY" in text
    assert "Último sondeo validado" in text
    assert "/menu" not in text


def test_render_prediction_fails_closed_without_snapshot(tmp_path, monkeypatch):
    monkeypatch.setattr(telegram_bot, "SNAPSHOT", tmp_path / "missing.json")
    monkeypatch.setattr(telegram_bot, "ESTIMATION", tmp_path / "missing-estimation.json")
    text = telegram_bot.render_command("/prediccion")
    assert "SITUACIÓN ACTUAL" in text
    assert "No se publica una cifra de escaños" in text
    assert "BLOQUEADA" not in text


def test_render_polls_uses_materialized_state(tmp_path, monkeypatch):
    state = tmp_path / "state.json"
    state.write_text(json.dumps({
        "status": "OK",
        "validated_polls": [{
            "publication_date": "2026-10-08",
            "pollster": "Fuente primaria",
            "parties": {"PP": 33.2, "PSOE": 28.1, "VOX": 13.0, "SUMAR": 12.2, "ERC": 3.1},
        }],
    }), encoding="utf-8")
    monkeypatch.setattr(telegram_bot, "STATE", state)
    monkeypatch.setattr(telegram_bot, "OBSERVATIONS", tmp_path / "missing-observations.json")
    text = telegram_bot.render_command("/encuestas")
    assert "Fuente primaria" in text
    assert "PP 33.2%" in text


def test_render_unknown_command_is_neutral():
    assert "no reconocido" in telegram_bot.render_command("/inventado").lower()


def test_token_fails_closed(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    try:
        telegram_bot._token()
    except telegram_bot.TelegramBotError:
        pass
    else:
        raise AssertionError("missing token must fail closed")


def test_render_changes_and_territory_are_fail_closed(tmp_path, monkeypatch):
    observations = tmp_path / "observations.json"
    observations.write_text(json.dumps({
        "national_poll_count": 2,
        "territorial_poll_count": 0,
        "polls": [
            {"publication_date": "2026-10-08", "pollster": "CIS",
             "parties": {"PSOE": 31.0, "PP": 25.0, "VOX": 16.0}},
            {"publication_date": "2026-09-07", "pollster": "CIS",
             "parties": {"PSOE": 33.0, "PP": 25.1, "VOX": 15.3}}
        ]
    }), encoding="utf-8")
    monkeypatch.setattr(telegram_bot, "OBSERVATIONS", observations)
    monkeypatch.setattr(telegram_bot, "STATE", tmp_path / "missing-state.json")
    text = telegram_bot.render_command("/cambios")
    assert "PSOE: -2.0 pp" in text
    territory = telegram_bot.render_command("/territorio")
    assert "distribución territorial explícita" in territory
    assert "BLOQUEADO" not in territory


def test_audit_exposes_real_blockers(tmp_path, monkeypatch):
    execution = tmp_path / "execution.json"
    execution.write_text(json.dumps({
        "current_phase": "OPERATIONAL_BETA",
        "blocked_tasks": ["PRIMARY_BINARY_NOT_REPOSITORY_PINNED", "OOS_CALIBRATION"],
        "warnings": ["strict certification blocked"],
    }), encoding="utf-8")
    oos = tmp_path / "oos.json"
    oos.write_text(json.dumps({
        "status": "NOT_STRICTLY_CERTIFIED",
        "elections": 8,
        "poll_observations": 28,
    }), encoding="utf-8")
    monkeypatch.setattr(telegram_bot, "EXECUTION", execution)
    monkeypatch.setattr(telegram_bot, "OOS", oos)
    text = telegram_bot.render_command("/auditoria")
    assert "Comprobaciones pendientes: 2" in text
    assert "PRIMARY_BINARY_NOT_REPOSITORY_PINNED" not in text
    assert "NOT_STRICTLY_CERTIFIED" in text
    assert "Advertencias registradas: 1" in text


def test_callback_menu_sends_keyboard(monkeypatch):
    calls = []
    monkeypatch.setattr(telegram_bot, "_api", lambda method, **kwargs: calls.append((method, kwargs)) or {"ok": True})
    update = {
        "update_id": 7,
        "callback_query": {
            "id": "cb1",
            "data": "cmd:/estado",
            "message": {"chat": {"id": 123}},
        },
    }
    assert telegram_bot._handle_update(update, None) == 8
    assert any(method == "answerCallbackQuery" for method, _ in calls)
    assert any(method == "sendMessage" for method, _ in calls)


def test_natural_questions_route_to_useful_answers():
    assert "PANEL DE HOY" in telegram_bot.render_command(telegram_bot._natural_query("¿Qué está pasando ahora?"))
    assert "CAMBIOS" in telegram_bot.render_command(telegram_bot._natural_query("¿Qué ha cambiado?"))
    assert "ENCUESTAS" in telegram_bot.render_command(telegram_bot._natural_query("¿Qué dicen los sondeos?"))
    assert "MAYORÍAS" in telegram_bot.render_command(telegram_bot._natural_query("¿Qué mayorías son posibles?"))


def test_user_never_sees_internal_prediction_blocker():
    text = telegram_bot.render_command("/escanos")
    assert "BLOCKED_NO_TERRITORIAL_INPUT" not in text
    assert "BLOQUEADO" not in text


def test_menu_uses_question_language():
    markup = telegram_bot._menu_markup()
    labels = [button["text"] for row in markup["inline_keyboard"] for button in row]
    assert "🟦 ¿Qué pasa ahora?" in labels
    assert "🗳 ¿Qué dicen los sondeos?" in labels
    assert "📅 ¿Qué plazos importan?" in labels


def test_month_situation_centre_is_available():
    text = telegram_bot.render_command("/mes")
    assert "CENTRO DE SITUACIÓN" in text
    assert "29/11/2026" in text
    assert "PRIORIDADES OPERATIVAS" in text


def test_calendar_uses_official_timeline():
    text = telegram_bot.render_command("/calendario")
    assert "PRÓXIMOS HITOS" in text
    assert "2026-10-16" in text



def test_public_text_never_leaks_internal_failure_terms():
    from src.telegram_bot import _public_text

    text = _public_text("BLOCKED: ERROR Exception BLOQUEADO")
    assert "BLOCKED" not in text
    assert "ERROR" not in text
    assert "Exception" not in text
    assert "BLOQUEADO" not in text


def test_public_text_has_nonempty_fallback():
    from src.telegram_bot import _public_text

    assert _public_text("").startswith("🟦 COALICIÓN")
