import json

from src import telegram_bot


def test_start_is_operational_menu():
    text = telegram_bot.render_command("/start")
    assert "SALA DE SITUACIÓN" in text
    assert "29/11/2026" in text
    assert "/menu" not in text


def test_render_prediction_fails_closed_without_snapshot(tmp_path, monkeypatch):
    monkeypatch.setattr(telegram_bot, "SNAPSHOT", tmp_path / "missing.json")
    monkeypatch.setattr(telegram_bot, "ESTIMATION", tmp_path / "missing-estimation.json")
    text = telegram_bot.render_command("/prediccion")
    assert "SITUACIÓN ACTUAL" in text
    assert "requiere evidencia provincial explícita" in text
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
    assert "verificación OOS pendiente" in text
    assert "Advertencias registradas: 1" in text


def test_callback_menu_edits_existing_message(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(telegram_bot, "USER_STATE", tmp_path / "state.json")
    monkeypatch.setattr(telegram_bot, "_api", lambda method, **kwargs: calls.append((method, kwargs)) or {"ok": True})
    update = {
        "update_id": 7,
        "callback_query": {
            "id": "cb1",
            "from": {"id": 42},
            "data": "cmd:/estado",
            "message": {"chat": {"id": 123}, "message_id": 77},
        },
    }
    assert telegram_bot._handle_update(update, None) == 8
    assert any(method == "answerCallbackQuery" for method, _ in calls)
    assert any(method == "editMessageText" for method, _ in calls)


def test_briefing_is_the_executive_start_screen():
    text = telegram_bot.render_command("/briefing")
    assert "SALA DE SITUACIÓN" in text
    assert "PRÓXIMO HITO" in text
    assert "LO QUE REQUIERE ATENCIÓN" in text


def test_natural_questions_route_to_useful_answers():
    assert "PANEL DE HOY" in telegram_bot.render_command(telegram_bot._natural_query("¿Qué está pasando ahora?"))
    assert "SALA DE SITUACIÓN" in telegram_bot.render_command(telegram_bot._natural_query("¿Qué debo saber ahora mismo?"))
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


def test_public_text_sanitizes_case_insensitive_internal_terms():
    from src.telegram_bot import _public_text
    text = _public_text("blocked_no_territorial_input BLOQUEADA Error Exception NOT_STRICTLY_CERTIFIED")
    assert "blocked" not in text.lower()
    assert "bloqueada" not in text.lower()
    assert "error" not in text.lower()
    assert "exception" not in text.lower()
    assert "not_strictly_certified" not in text.lower()
    assert "COMPROBACIÓN PENDIENTE" in text


def test_public_text_has_nonempty_fallback():
    from src.telegram_bot import _public_text

    assert _public_text("").startswith("🟦 COALICIÓN")


def test_send_splits_long_public_response(monkeypatch):
    calls = []
    monkeypatch.setattr(telegram_bot, "_api", lambda method, **kwargs: calls.append((method, kwargs)) or {"ok": True})
    telegram_bot._send(123, "A" * (telegram_bot.MAX_MESSAGE + 100))
    texts = [kwargs["json"]["text"] for method, kwargs in calls if method == "sendMessage"]
    assert len(texts) == 2
    assert "".join(texts) == "A" * (telegram_bot.MAX_MESSAGE + 100)
    assert all(len(x) <= telegram_bot.MAX_MESSAGE for x in texts)



def test_callback_navigation_edits_same_message_and_persists_back(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(telegram_bot, "USER_STATE", tmp_path / "user_state.json")
    monkeypatch.setattr(
        telegram_bot,
        "_api",
        lambda method, **kwargs: calls.append((method, kwargs)) or {"ok": True},
    )
    first = {
        "update_id": 10,
        "callback_query": {
            "id": "cb1",
            "from": {"id": 42},
            "data": "cmd:/encuestas",
            "message": {"chat": {"id": 123}, "message_id": 77},
        },
    }
    assert telegram_bot._handle_update(first, None) == 11
    assert any(method == "editMessageText" for method, _ in calls)
    assert not any(method == "sendMessage" for method, _ in calls)

    calls.clear()
    second = {
        "update_id": 11,
        "callback_query": {
            "id": "cb2",
            "from": {"id": 42},
            "data": "back",
            "message": {"chat": {"id": 123}, "message_id": 77},
        },
    }
    assert telegram_bot._handle_update(second, 11) == 12
    edits = [kwargs["json"] for method, kwargs in calls if method == "editMessageText"]
    assert edits
    assert "SALA DE SITUACIÓN" in edits[-1]["text"]


def test_navigation_markup_has_back_home_refresh():
    markup = telegram_bot._navigation_markup("/encuestas")
    labels = [button["text"] for row in markup["inline_keyboard"] for button in row]
    assert "← Atrás" in labels
    assert "🏠 Inicio" in labels
    assert "🔄 Actualizar" in labels


def test_home_navigation_markup_has_refresh_and_drilldown():
    markup = telegram_bot._navigation_markup("/briefing")
    labels = [button["text"] for row in markup["inline_keyboard"] for button in row]
    assert "🔄 Actualizar" in labels
    assert "🧭 Inicio" in labels
    assert "📈 Cambios" in labels



def test_alert_preferences_toggle_and_frequency(tmp_path, monkeypatch):
    monkeypatch.setattr(telegram_bot, "TELEGRAM_CONFIG", tmp_path / "telegram_config.json")
    update = {"message": {"chat": {"id": 123, "type": "private"}, "from": {"id": 42}}}
    prefs = telegram_bot._preferences(update)
    assert prefs["categories"]["nueva_encuesta"] is True
    telegram_bot._set_preferences(update, categories={**prefs["categories"], "nueva_encuesta": False}, frequency="daily")
    saved = telegram_bot._preferences(update)
    assert saved["categories"]["nueva_encuesta"] is False
    assert saved["frequency"] == "daily"


def test_public_inline_query_returns_article(monkeypatch):
    calls = []
    monkeypatch.setattr(telegram_bot, "_api", lambda method, **kwargs: calls.append((method, kwargs)) or {"ok": True})
    update = {"update_id": 1, "inline_query": {"id": "iq1", "query": "ponme al día", "from": {"id": 42}}}
    telegram_bot._handle_update(update, None)
    payloads = [kwargs["json"] for method, kwargs in calls if method == "answerInlineQuery"]
    assert payloads
    assert payloads[0]["results"][0]["type"] == "article"


def test_poll_card_has_evidence_and_pagination(tmp_path, monkeypatch):
    observations = tmp_path / "observations.json"
    observations.write_text(json.dumps({
        "polls": [
            {"publication_date": "2026-10-08", "pollster": "CIS", "parties": {"PP": 33.0}},
            {"publication_date": "2026-10-01", "pollster": "CIS", "parties": {"PP": 32.0}},
        ]
    }), encoding="utf-8")
    monkeypatch.setattr(telegram_bot, "OBSERVATIONS", observations)
    monkeypatch.setattr(telegram_bot, "STATE", tmp_path / "state.json")
    markup = telegram_bot._poll_card_markup(0)
    data = [b["callback_data"] for row in markup["inline_keyboard"] for b in row]
    assert "evidence:poll:1" in data
    assert "evidence:detail:0" in data


def test_export_payload_supports_csv_json_pdf(tmp_path, monkeypatch):
    observations = tmp_path / "observations.json"
    observations.write_text(json.dumps({
        "polls": [{"publication_date": "2026-10-08", "pollster": "CIS", "parties": {"PP": 33.0}}]
    }), encoding="utf-8")
    monkeypatch.setattr(telegram_bot, "OBSERVATIONS", observations)
    monkeypatch.setattr(telegram_bot, "STATE", tmp_path / "state.json")
    csv_data, csv_name, _ = telegram_bot._export_payload("csv")
    assert csv_name.endswith(".csv")
    assert b"publication_date" in csv_data
    pdf_data, pdf_name, _ = telegram_bot._export_payload("pdf")
    assert pdf_name.endswith(".pdf")
    assert pdf_data.startswith(b"%PDF")


def test_rate_limit_private_is_fail_closed(monkeypatch):
    telegram_bot._RATE.clear()
    update = {"message": {"chat": {"id": 123, "type": "private"}, "from": {"id": 42}}}
    for _ in range(10):
        assert telegram_bot._rate_allowed(update) is True
    assert telegram_bot._rate_allowed(update) is False
