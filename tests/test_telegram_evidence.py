from src.telegram_bot import render_command

def test_territorial_evidence_command_exposes_traceability():
    text = render_command("/evidencia sigma_dos_asturias_20260908")
    assert "EVIDENCIA · TERRITORIAL" in text
    assert "Fuente: sigma_dos" in text
    assert "Muestra: 1129" in text
    assert "Hash:" in text
    assert "No se convierte esta encuesta" in text

def test_unknown_territorial_evidence_is_fail_closed():
    text = render_command("/evidencia does_not_exist")
    assert "No existe una encuesta territorial materializada" in text
