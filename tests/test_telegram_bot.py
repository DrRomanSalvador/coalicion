import json

from src import telegram_bot


def test_render_prediction_fails_closed_without_snapshot(tmp_path, monkeypatch):
    monkeypatch.setattr(telegram_bot, "SNAPSHOT", tmp_path / "missing.json")
    text = telegram_bot.render_command("/prediccion")
    assert "BLOQUEADA" in text
    assert "inferencia" in text


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
