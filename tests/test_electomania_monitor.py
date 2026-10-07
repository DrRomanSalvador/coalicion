from src.monitors.electomania_monitor import ElectomaniaMonitor

def test_electomania_adapter_extracts_explicit_values():
    html=b"""<html><head><title>Encuesta</title></head><body>
    <h1>Sondeo para elecciones generales</h1><p>01/10/2026</p>
    <p>Partido | Voto (%) | Escanos</p>
    <p>PP 33,8% PSOE 25,9% VOX 18,8% Sumar 5,9% Podemos 3,8% ERC 2,0%</p>
    </body></html>"""
    polls, discoveries=ElectomaniaMonitor({"id":"electomania","url":"https://example.test","pollster":"Demo"}, None).parse(html)
    assert len(polls)==1
    assert polls[0].parties["PP"]==33.8
    assert discoveries==[]
