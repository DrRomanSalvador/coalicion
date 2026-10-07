import json
from pathlib import Path

from src.poll_monitor import Poll, normalize_party_name, poll_hash, validate_poll, parse_rss_metadata, parse_dato_electoral

def valid_poll():
    return Poll("p1","2026-10-07","Demo","x","https://example.test",
                {"PSOE":31.0,"PP":25.0,"VOX":16.0,"SUMAR":6.0,"PODEMOS":4.0,
                 "ERC":2.0,"JUNTS":2.0,"BNG":1.0,"OTROS PARTIDOS":13.0})

def test_normalize_party_name():
    assert normalize_party_name("Partido Popular") == "PP"
    assert normalize_party_name("Sumar") == "SUMAR"

def test_validate_poll_fail_closed():
    ok, reason = validate_poll(valid_poll())
    assert ok and reason == "OK"
    bad = Poll("p2","2026-10-07","Demo","x","https://example.test",{"PSOE":30.0})
    assert validate_poll(bad)[0] is False

def test_poll_hash_is_deterministic():
    assert poll_hash(valid_poll()) == poll_hash(valid_poll())

def test_rss_is_discovery_only():
    rss=b'''<rss><channel><item><title>Barómetro</title><link>https://example.test/p1</link><guid>p1</guid><pubDate>Wed, 07 Oct 2026 08:00:00 +0000</pubDate></item></channel></rss>'''
    rows=parse_rss_metadata(rss,{"id":"cis","url":"https://example.test"})
    assert rows[0]["validation"]=="DISCOVERY_ONLY"
    assert "parties" not in rows[0]

def test_dato_parser_rejects_questionnaire_percentages():
    html=b'''<h3>Barómetro de prueba 2026</h3>
    <p>Demo · publicado el 7 de octubre de 2026 · ámbito: España</p>
    <h4>Estimación de voto publicada por el sondeo</h4>
    <p>PSOE 31,0 %</p><p>PP 25,0 %</p><p>VOX 16,0 %</p>
    <p>SUMAR 6,0 %</p><p>PODEMOS 4,0 %</p><p>ERC 2,0 %</p><p>JUNTS 2,0 %</p>
    <p>BNG 1,0 %</p><p>OTROS PARTIDOS 13,0 %</p>
    <p>Pregunta cuestionario 50 %</p>'''
    rows=parse_dato_electoral(html,{"id":"dato","url":"https://example.test"})
    assert len(rows)==1
    assert rows[0].parties["PSOE"]==31.0
    assert "PREGUNTA CUESTIONARIO" not in rows[0].parties

def test_poll_monitor_module_loads_config():
    cfg=json.loads(Path("config/poll_monitor.json").read_text())
    assert cfg["policy"]["fail_closed"] is True
    assert len(cfg["sources"]) >= 10

def test_validate_poll_rejects_impossible_calendar_date():
    poll = Poll("bad-date","2026-02-30","Demo","x","https://example.test",
                {"PSOE":31.0,"PP":25.0,"VOX":16.0,"SUMAR":6.0,"PODEMOS":4.0,
                 "ERC":2.0,"JUNTS":2.0,"BNG":1.0,"OTROS PARTIDOS":13.0})
    assert validate_poll(poll) == (False, "INVALID_PUBLICATION_DATE")

def test_page_fingerprint_is_not_an_election_alert():
    from src.poll_monitor import SourceMonitor
    import requests
    monitor = SourceMonitor({"id":"page","url":"https://example.test","format":"page"}, requests.Session())
    polls, discoveries = monitor.parse(b"changed page")
    assert polls == []
    assert discoveries[0]["validation"] == "PAGE_FINGERPRINT_ONLY"
    assert discoveries[0]["alertable"] is False
