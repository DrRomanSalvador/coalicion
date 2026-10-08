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
    monkeypatch.setattr(telegram_bot, "STATE", state)\n    monkeypatch.setattr(telegram_bot, "OBSERVATIONS", tmp_path / "missing-observations.json")
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


def test_render_uses_materialized_observations_and_explains_territorial_block(tmp_path, monkeypatch):
    observations = tmp_path / "observations.json"
    observations.write_text(json.dumps({
        "status": "BLOCKED_NO_TERRITORIAL_OBSERVATION",
        "national_poll_count": 2,
        "territorial_poll_count": 0,
        "polls": [
            {"publication_date": "2026-10-08", "pollster": "CIS", "parties": {"PSOE": 31.0, "PP": 25.0, "VOX": 16.0}},
            {"publication_date": "2026-09-07", "pollster": "CIS", "parties": {"PSOE": 33.0, "PP": 25.1, "VOX": 15.3}}
        ]
    }), encoding="utf-8")
    monkeypatch.setattr(telegram_bot, "OBSERVATIONS", observations)
    monkeypatch.setattr(telegram_bot, "STATE", tmp_path / "missing-state.json")
    text = telegram_bot.render_command("/encuestas")
    assert "2 observaciones validadas" in text
    assert "PSOE -2.0 pp" in text
    assert "Territoriales explícitas: 0/ 2" in text
    assert "BLOQUEADOS" in text

def test_render_status_uses_materialized_observations(tmp_path, monkeypatch):
    observations = tmp_path / "observations.json"
    observations.write_text(json.dumps({
        "territorial_poll_count": 0,
        "polls": [{"publication_date": "2026-10-08", "parties": {"PP": 25.0}}]
    }), encoding="utf-8")
    estimation = tmp_path / "estimation.json"
    estimation.write_text(json.dumps({"status": "BLOCKED"}), encoding="utf-8")
    monkeypatch.setattr(telegram_bot, "OBSERVATIONS", observations)
    monkeypatch.setattr(telegram_bot, "ESTIMATION", estimation)
    monkeypatch.setattr(telegram_bot, "STATE", tmp_path / "missing-state.json")
    text = telegram_bot.render_command("/estado")
    assert "Observaciones validadas: 1" in text
    assert "Predicción: BLOCKED" in text
    assert "sin inferencia nacional→territorial" in text

def test_render_radar_exposes_operational_alerts(tmp_path, monkeypatch):
    estimation = tmp_path / "estimation.json"
    estimation.write_text(json.dumps({
        "status": "BLOCKED",
        "radar": {"status": "OK", "as_of": "2026-10-08",
                  "alerts": [{"priority": "P4", "title": "Cierre de coaliciones", "facts": {"days_remaining": 8}}]}
    }), encoding="utf-8")
    monkeypatch.setattr(telegram_bot, "ESTIMATION", estimation)
    text = telegram_bot.render_command("/radar")
    assert "Cierre de coaliciones" in text
    assert "BLOQUEO PREDICTIVO" in text
