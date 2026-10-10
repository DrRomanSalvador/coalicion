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



def test_private_admin_is_authorized_by_user_id(monkeypatch, tmp_path):
    monkeypatch.delenv("TELEGRAM_ALLOWED_CHATS", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.setenv("TELEGRAM_ADMIN_IDS", "42")
    monkeypatch.setattr(telegram_bot, "USER_STATE", tmp_path / "state.json")
    calls = []
    monkeypatch.setattr(telegram_bot, "_api", lambda method, **kwargs: calls.append((method, kwargs)) or {"ok": True})
    update = {
        "update_id": 8,
        "message": {
            "from": {"id": 42},
            "chat": {"id": 42, "type": "private"},
            "text": "/ayuda",
        },
    }
    assert telegram_bot._handle_update(update, None) == 9
    assert any(method == "sendMessage" for method, _ in calls)


def test_unauthorized_chat_sends_access_request_to_operator(monkeypatch, tmp_path):
    monkeypatch.delenv("TELEGRAM_ALLOWED_CHATS", raising=False)
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "7")
    monkeypatch.delenv("TELEGRAM_ADMIN_IDS", raising=False)
    monkeypatch.setattr(telegram_bot, "TELEGRAM_CONFIG", tmp_path / "telegram_config.json")
    calls = []
    monkeypatch.setattr(telegram_bot, "_api", lambda method, **kwargs: calls.append((method, kwargs)) or {"ok": True})
    update = {
        "update_id": 9,
        "message": {
            "from": {"id": 42, "first_name": "Ada", "username": "ada"},
            "chat": {"id": 42, "type": "private"},
            "text": "Quiero acceder a COALICIÓN",
        },
    }
    assert telegram_bot._handle_update(update, None) == 10
    messages = [kwargs["json"] for method, kwargs in calls if method == "sendMessage"]
    assert any("ID de chat: 42" in m["text"] and "No tienes que configurar secretos" in m["text"] for m in messages)
    owner = next(m for m in messages if m["chat_id"] == 7)
    assert "ID de usuario: 42" in owner["text"]
    assert "Quiero acceder a COALICIÓN" in owner["text"]
    assert owner["reply_markup"]["inline_keyboard"][0][0]["callback_data"] == "access:approve:42:42"


def test_operator_approves_user_from_telegram_without_secrets_edit(monkeypatch, tmp_path):
    monkeypatch.delenv("TELEGRAM_ALLOWED_CHATS", raising=False)
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "7")
    monkeypatch.delenv("TELEGRAM_ADMIN_IDS", raising=False)
    monkeypatch.setattr(telegram_bot, "TELEGRAM_CONFIG", tmp_path / "telegram_config.json")
    telegram_bot._save_config({
        "users": {}, "chats": {},
        "access_requests": {"42:42": {"chat_id": "42", "user_id": "42", "name": "Ada", "username": "ada", "message": "Hola", "chat_type": "private"}},
        "authorized_users": [], "authorized_chats": [],
    })
    calls = []
    monkeypatch.setattr(telegram_bot, "_api", lambda method, **kwargs: calls.append((method, kwargs)) or {"ok": True})
    update = {
        "update_id": 10,
        "callback_query": {
            "id": "approve1", "from": {"id": 7}, "data": "access:approve:42:42",
            "message": {"chat": {"id": 7, "type": "private"}, "message_id": 5},
        },
    }
    assert telegram_bot._handle_update(update, None) == 11
    assert "42" in telegram_bot._config()["authorized_users"]
    assert telegram_bot._config()["access_requests"] == {}
    assert telegram_bot._owner_allowed(update)


def test_callback_menu_edits_existing_message(monkeypatch, tmp_path):
    monkeypatch.setenv("TELEGRAM_ALLOWED_CHATS", "123")
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

def test_escanos_fails_closed_on_demo_or_unvalidated_projection(tmp_path, monkeypatch):
    snapshot = tmp_path / "snapshot.json"
    demo = tmp_path / "demo.json"
    snapshot.write_text(json.dumps({
        "projection": {
            "status": "PASS",
            "calibration_status": "PASS",
            "territorial_poll_count": 0,
            "national_seats": {"PARTY_A": 180}
        }
    }), encoding="utf-8")
    demo.write_text(json.dumps({
        "status": "PASS",
        "national_seats": {"PARTY_A": 180}
    }), encoding="utf-8")
    monkeypatch.setattr(telegram_bot, "SNAPSHOT", snapshot)
    monkeypatch.setattr(telegram_bot, "DEMO_PREDICTION", demo)
    result = telegram_bot._escanos_text()
    assert "no hay una proyección" in result.lower()
    assert "PARTY_A: 180" not in result


def test_escanos_requires_both_territorial_evidence_and_calibration(tmp_path, monkeypatch):
    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text(json.dumps({
        "projection": {
            "status": "PASS",
            "calibration_status": "PASS",
            "territorial_poll_count": 1,
            "national_seats": {"PARTY_A": 180, "PARTY_B": 170}
        }
    }), encoding="utf-8")
    monkeypatch.setattr(telegram_bot, "SNAPSHOT", snapshot)
    assert "PARTY_A: 180" in telegram_bot._escanos_text()


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
    monkeypatch.setenv("TELEGRAM_ALLOWED_CHATS", "123")
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
    monkeypatch.setenv("TELEGRAM_ALLOWED_CHATS", "42")
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


def test_export_pdf_falls_back_when_reportlab_is_unavailable(tmp_path, monkeypatch):
    import builtins

    observations = tmp_path / "observations.json"
    observations.write_text(json.dumps({
        "polls": [{"publication_date": "2026-10-08", "pollster": "CIS", "parties": {"PP": 33.0}}]
    }), encoding="utf-8")
    monkeypatch.setattr(telegram_bot, "OBSERVATIONS", observations)
    monkeypatch.setattr(telegram_bot, "STATE", tmp_path / "state.json")
    original_import = builtins.__import__

    def import_without_reportlab(name, *args, **kwargs):
        if name == "reportlab" or name.startswith("reportlab."):
            raise ImportError("ReportLab intentionally unavailable in this regression test")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", import_without_reportlab)
    pdf_data, filename, content_type = telegram_bot._export_payload("pdf")
    assert filename.endswith(".pdf")
    assert content_type == "application/pdf"
    assert pdf_data.startswith(b"%PDF-1.4")
    assert b"startxref" in pdf_data
    assert b"%%EOF" in pdf_data


def test_rate_limit_private_is_fail_closed(monkeypatch):
    telegram_bot._RATE.clear()
    update = {"message": {"chat": {"id": 123, "type": "private"}, "from": {"id": 42}}}
    for _ in range(10):
        assert telegram_bot._rate_allowed(update) is True
    assert telegram_bot._rate_allowed(update) is False



def test_interactive_comparison_periods(tmp_path, monkeypatch):
    observations = tmp_path / "observations.json"
    observations.write_text(json.dumps({
        "polls": [
            {"publication_date": "2026-10-08", "parties": {"PP": 34.0}},
            {"publication_date": "2026-10-07", "parties": {"PP": 33.0}},
            {"publication_date": "2026-10-06", "parties": {"PP": 32.0}},
            {"publication_date": "2026-10-05", "parties": {"PP": 31.0}},
            {"publication_date": "2026-10-04", "parties": {"PP": 30.0}},
        ]
    }), encoding="utf-8")
    monkeypatch.setattr(telegram_bot, "OBSERVATIONS", observations)
    monkeypatch.setattr(telegram_bot, "STATE", tmp_path / "state.json")
    assert "5 observaciones" in telegram_bot._comparison_text("5")
    assert "PP: +4.0 pp" in telegram_bot._comparison_text("5")
    labels = [b["text"] for row in telegram_bot._comparison_markup()["inline_keyboard"] for b in row]
    assert "5 observaciones" in labels
    assert "30 días" in labels



def test_territory_navigation_is_hierarchical(tmp_path, monkeypatch):
    matrix = tmp_path / "artifacts" / "data" / "election_2023_canonical.json"
    matrix.parent.mkdir(parents=True)
    matrix.write_text(json.dumps({"data": {"constituencies": {
        "Madrid": {"seats": 37, "valid_votes": 1000, "parties": {"PP": 500, "PSOE": 400}}
    }}}), encoding="utf-8")
    monkeypatch.setattr(telegram_bot, "ROOT", tmp_path)
    root_markup = telegram_bot._territory_markup("ES")
    assert any("territory:region:" in b["callback_data"] for row in root_markup["inline_keyboard"] for b in row)
    detail = telegram_bot._territory_detail("Madrid")
    assert "Madrid" in detail and "Escaños: 37" in detail


def test_inline_callback_edits_inline_message(monkeypatch):
    telegram_bot._RATE.clear()
    calls = []
    monkeypatch.setattr(telegram_bot, "_api", lambda method, **kwargs: calls.append((method, kwargs)) or {"ok": True})
    update = {"update_id": 9, "callback_query": {
        "id": "cb", "from": {"id": 42}, "inline_message_id": "abc",
        "data": "cmd:/briefing"
    }}
    telegram_bot._handle_update(update, None)
    assert any(method == "editMessageText" and kwargs["json"]["inline_message_id"] == "abc" for method, kwargs in calls)



def test_export_text_dispatches_document(monkeypatch):
    calls = []
    monkeypatch.setattr(telegram_bot, "_export_payload", lambda kind: (b"data", "x.json", "application/json"))
    monkeypatch.setattr(telegram_bot, "_send_document", lambda *args: calls.append(args))
    telegram_bot._export_text(123, "polls")
    assert calls == [(123, b"data", "x.json", "application/json")]



def test_situation_command_uses_canonical_state(tmp_path, monkeypatch):
    observations = tmp_path / "observations.json"
    observations.write_text(json.dumps({"policy": {"observed_only": True, "national_to_territorial_inference": False}, "national_poll_count": 1, "territorial_poll_count": 0, "polls": [{"poll_id": "poll-1", "publication_date": "2026-10-08", "parties": {"PP": 34.0, "PSOE": 30.0}, "source_url": "https://example.invalid/poll"}]}), encoding="utf-8")
    coverage = tmp_path / "coverage.json"
    coverage.write_text(json.dumps({"fail_closed": True, "primary_sources": 1, "healthy_primary_sources": 1, "unhealthy_primary_sources": [], "status": "PASS", "last_runtime_coverage": {"sources_checked": 1}}), encoding="utf-8")
    mission = tmp_path / "mission.json"
    mission.write_text(json.dumps({"fail_closed": True, "id": "test"}), encoding="utf-8")
    import src.situation_state as ss
    monkeypatch.setattr(ss, "OBSERVATIONS", observations)
    monkeypatch.setattr(ss, "SOURCE_COVERAGE", coverage)
    monkeypatch.setattr(ss, "MISSION", mission)
    text = telegram_bot.render_command("/situacion")
    assert "SALA DE SITUACIÓN" in text
    assert "UNCERTAINTY" in text
    assert "Observaciones territoriales 2026: 0" in text


def test_demo_does_not_present_blocked_seat_values(tmp_path, monkeypatch):
    demo = tmp_path / "demo.json"
    demo.write_text(json.dumps({
        "status": "BLOCKED",
        "national_seats": {"PARTY_A": 180},
        "blockers": ["BLOCKED_NO_TERRITORIAL_INPUT"]
    }), encoding="utf-8")
    monkeypatch.setattr(telegram_bot, "DEMO_PREDICTION", demo)
    result = telegram_bot._demo_prediction_text()
    assert "BLOQUEADA" in result
    assert "No se muestran escaños" in result
    assert "PARTY_A: 180" not in result
    assert "BLOCKED_NO_TERRITORIAL_INPUT" not in result


def test_demo_blocks_false_pass_without_territorial_calibration_or_seat_invariant(tmp_path, monkeypatch):
    demo = tmp_path / "demo.json"
    demo.write_text(json.dumps({
        "status": "PASS",
        "territorial_input": "NONE",
        "observed_territorial_polls": 0,
        "calibration_status": "NOT_2026_CALIBRATED",
        "seat_total": 180,
        "national_seats": {"PARTY_A": 180},
        "blockers": []
    }), encoding="utf-8")
    monkeypatch.setattr(telegram_bot, "DEMO_PREDICTION", demo)
    result = telegram_bot._demo_prediction_text()
    assert "BLOQUEADA" in result
    assert "PARTY_A: 180" not in result


def test_bounded_polling_drains_queue_without_waiting(monkeypatch):
    calls = []
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setattr(telegram_bot, "restore_telegram_state", lambda: None)
    monkeypatch.setattr(telegram_bot, "snapshot_telegram_state", lambda: None)
    monkeypatch.setattr(telegram_bot, "_configure_bot_ui", lambda: None)
    monkeypatch.setattr(telegram_bot, "_maybe_send_scheduled_digest", lambda: None)
    monkeypatch.setattr(telegram_bot, "_load_poll_offset", lambda: None)
    monkeypatch.setattr(telegram_bot, "_save_poll_offset", lambda offset: None)
    monkeypatch.setattr(
        telegram_bot, "_api",
        lambda method, **kwargs: calls.append((method, kwargs)) or {"ok": True, "result": []},
    )

    telegram_bot.run_polling(max_runtime_seconds=45)

    polls = [(method, kwargs) for method, kwargs in calls if method == "getUpdates"]
    assert len(polls) == 1
    assert polls[0][1]["params"]["timeout"] == 0
    assert calls[0][0] == "deleteWebhook"
