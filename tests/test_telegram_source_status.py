import json
from pathlib import Path

from src.telegram_bot import _sources, render_command


def test_sources_reads_materialized_source_status():
    path = Path("artifacts/poll_monitor_state.json")
    assert path.exists()
    state = json.loads(path.read_text(encoding="utf-8"))
    source_status = state.get("source_status")
    assert isinstance(source_status, dict) and source_status
    sources = _sources()
    assert len(sources) == len(source_status)
    assert {x["id"] for x in sources} == set(source_status)
    rendered = render_command("/fuentes")
    assert str(len(source_status)) in rendered or any(source_id in rendered for source_id in source_status)


def test_situacion_uses_materialized_source_status():
    text = render_command("/situacion")
    assert "FUENTES" in text.upper()
    assert "No hay estado reciente" not in text
