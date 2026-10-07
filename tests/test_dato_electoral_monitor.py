from src.monitors.dato_electoral_monitor import DatoElectoralMonitor

def test_dato_electoral_adapter_uses_explicit_estimation_block():
    html=b"""<h3>Barometro</h3><p>Demo · publicado el 7 de octubre de 2026</p>
    <h4>Estimación de voto publicada por el sondeo</h4>
    <p>PSOE 31,0 %</p><p>PP 25,0 %</p><p>VOX 16,0 %</p><p>SUMAR 6,0 %</p><p>PODEMOS 4,0 %</p><p>ERC 2,0 %</p>"""
    polls, discoveries=DatoElectoralMonitor({"id":"dato","url":"https://example.test"}, None).parse(html)
    assert len(polls)==1
    assert polls[0].parties["PSOE"]==31.0
    assert discoveries==[]
