from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "web/demo/index.html"


def test_decision_ui_exposes_core_decision_functions():
    html = PAGE.read_text(encoding="utf-8")
    for expected in (
        'lang="es"',
        'COALICION_DECISION_ANALYSIS_V1',
        'artifacts/demo_decision_analysis_2023.json',
        'marginal_seat_changes',
        'viability_frontier',
        'decision_log',
        'source_workbook_sha256',
        'Exportar registro JSON',
        'No se puede deducir',
        'NOT_INDEPENDENTLY_CERTIFIED',
    ):
        assert expected in html


def test_decision_ui_does_not_implement_an_electoral_allocator():
    html = PAGE.read_text(encoding="utf-8").lower()
    assert "d'hondt algorithm" not in html
    assert "function allocate(" not in html
    assert "function dhondt(" not in html
