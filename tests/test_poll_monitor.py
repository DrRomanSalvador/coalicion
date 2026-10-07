import json
from pathlib import Path

from src.poll_monitor import Poll, normalize_party_name, poll_hash, poll_identity, validate_poll, parse_rss_metadata, parse_dato_electoral, parse_national_html

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
    rss = """<rss><channel><item><title>Barómetro</title><link>https://example.test/p1</link><guid>p1</guid><pubDate>Wed, 07 Oct 2026 08:00:00 +0000</pubDate></item></channel></rss>""".encode("utf-8")
    rows=parse_rss_metadata(rss,{"id":"cis","url":"https://example.test"})
    assert rows[0]["validation"]=="DISCOVERY_ONLY"
    assert "parties" not in rows[0]

def test_dato_parser_rejects_questionnaire_percentages():
    html = """<h3>Barómetro de prueba 2026</h3>
    <p>Demo · publicado el 7 de octubre de 2026 · ámbito: España</p>
    <h4>Estimación de voto publicada por el sondeo</h4>
    <p>PSOE 31,0 %</p><p>PP 25,0 %</p><p>VOX 16,0 %</p>
    <p>SUMAR 6,0 %</p><p>PODEMOS 4,0 %</p><p>ERC 2,0 %</p><p>JUNTS 2,0 %</p>
    <p>BNG 1,0 %</p><p>OTROS PARTIDOS 13,0 %</p>
    <p>Pregunta cuestionario 50 %</p>""".encode("utf-8")
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


def test_national_html_extracts_only_coherent_poll():
    html = """<html><head><title>Barómetro ABC</title></head><body>
    <h1>Barómetro ABC | Estimación de voto nacional. Septiembre 2026</h1>
    <p>7 de septiembre de 2026. Elecciones generales. GAD3 para ABC.</p>
    <p>PP 31,1% PSOE 26,1% Vox 19,2% Sumar 7,0% Podemos 3,0% ERC 2,0% Junts 1,5% PNV 1,2% BNG 1,0% Otros partidos 8,9%</p>
    </body></html>""".encode("utf-8")
    rows = parse_national_html(html, {"id":"gad3","name":"GAD3","pollster":"GAD3","url":"https://example.test"})
    assert len(rows) == 1
    assert rows[0].publication_date == "2026-09-07"
    assert rows[0].parties["PP"] == 31.1
    assert rows[0].parties["PSOE"] == 26.1


def test_national_html_rejects_poll_commentary_without_full_estimates():
    html = """<html><body><h1>Noticias electorales</h1>
    <p>Las últimas encuestas sitúan al PP por delante y a Vox al alza.</p>
    </body></html>""".encode("utf-8")
    assert parse_national_html(html, {"id":"x","name":"X","pollster":"X","url":"https://example.test"}) == []


def test_validate_poll_accepts_published_subset_without_manufacturing_residual():
    poll = Poll("subset","2026-10-07","Demo","x","https://example.test",
                {"PP":31.6,"PSOE":27.4,"VOX":18.4,"SUMAR":5.6,"PODEMOS":2.7})
    ok, reason = validate_poll(poll)
    assert ok and reason == "OK"


def test_coverage_contract_blocks_unstructured_primary_sources():
    from src.poll_monitor import PollMonitor
    monitor = PollMonitor.__new__(PollMonitor)
    monitor.config = {"coverage_contract":{"scope":"configured_national_poll_universe"},
                      "sources":[{"id":"primary","coverage_role":"primary","format":"page"}]}
    monitor.state = {"source_status":{"primary":{"status":"OK"}}}
    result = monitor.audit_coverage([], [])
    assert result["total"] is False
    assert "PRIMARY_WITHOUT_STRUCTURED_EXTRACTOR:primary" in result["blockers"]


def test_coverage_contract_can_reach_total_for_structured_healthy_sources():
    from src.poll_monitor import PollMonitor
    monitor = PollMonitor.__new__(PollMonitor)
    monitor.config = {"coverage_contract":{"scope":"configured_national_poll_universe"},
                      "sources":[{"id":"primary","coverage_role":"primary","format":"national_html"}]}
    monitor.state = {"source_status":{"primary":{"status":"OK"}}}
    result = monitor.audit_coverage([], [])
    assert result["total"] is True
    assert result["claim"] == "COBERTURA_TOTAL_VERIFICADA"


def test_coverage_manifest_is_structurally_valid():
    cfg = json.loads(Path("config/poll_monitor.json").read_text())
    active = [s for s in cfg["sources"] if not s.get("disabled")]
    assert cfg["coverage_contract"]["claim"] == "COBERTURA_TOTAL_VERIFICADA"
    assert all(s.get("coverage_role") in {"primary","discovery","optional"} for s in active)
    assert all("id" in s and "url" in s and "format" in s for s in active)
    assert len({s["id"] for s in active}) == len(active)
    by_id = {s["id"]: s for s in active}
    assert by_id["europe_elects_twitter"]["url"].endswith("/tweets")
    assert by_id["lasexta_invymark_discovery"]["url"].startswith("https://www.lasexta.com/")


def test_poll_identity_ignores_source_and_values():
    a = valid_poll()
    b = Poll(a.poll_id, a.publication_date, a.pollster, "mirror", "https://mirror.test",
             {**a.parties, "PP": 24.0}, a.fieldwork_start, a.fieldwork_end, a.sample_size, a.methodology)
    assert poll_identity(a) == poll_identity(b)


def test_replica_is_preserved_but_not_reported_as_new():
    from src.poll_monitor import PollMonitor
    monitor = PollMonitor.__new__(PollMonitor)
    monitor.state = {"poll_hashes": {}, "poll_identities": {}, "discovery_hashes": {}}
    first = valid_poll()
    second = Poll(first.poll_id + "-mirror", first.publication_date, first.pollster, "mirror",
                  "https://mirror.test", first.parties, first.fieldwork_start, first.fieldwork_end,
                  first.sample_size, first.methodology)
    new, changed, discoveries = monitor.detect_new([first, second], [])
    assert len(new) == 1
    assert changed == []
    assert monitor.state["poll_hashes"][second.poll_id]
    assert "replica_of" in monitor.state.get("last_replica", {}) or monitor.state["poll_identities"]


def test_coverage_blocks_failed_source_and_status_cannot_be_ready():
    from src.poll_monitor import PollMonitor
    monitor = PollMonitor.__new__(PollMonitor)
    monitor.config = {"coverage_contract":{"scope":"configured_national_poll_universe",
                                           "require_zero_unresolved_discoveries": True},
                      "sources":[{"id":"primary","coverage_role":"primary","format":"national_html"}]}
    monitor.state = {"source_status":{"primary":{"status":"FAILED"}}}
    result = monitor.audit_coverage([{"source_id":"primary","error":"timeout"}], [])
    assert result["total"] is False
    assert "SOURCE_NOT_HEALTHY:primary" in result["blockers"]


def test_optional_primary_source_blocks_total_coverage():
    from src.poll_monitor import PollMonitor
    monitor = PollMonitor.__new__(PollMonitor)
    monitor.config = {"coverage_contract":{"scope":"configured_national_poll_universe"}, "sources":[{"id":"primary","coverage_role":"primary","format":"national_html","optional":True}]}
    monitor.state = {"source_status":{"primary":{"status":"OK"}}}
    result = monitor.audit_coverage([], [])
    assert result["total"] is False
    assert "PRIMARY_CANNOT_BE_OPTIONAL:primary" in result["blockers"]

def test_unresolved_discovery_blocks_total_coverage():
    from src.poll_monitor import PollMonitor
    monitor = PollMonitor.__new__(PollMonitor)
    monitor.config = {"coverage_contract":{"scope":"configured_national_poll_universe","require_zero_unresolved_discoveries":True}, "sources":[{"id":"primary","coverage_role":"primary","format":"national_html"}]}
    monitor.state = {"source_status":{"primary":{"status":"OK"}}}
    result = monitor.audit_coverage([], [{"source_id":"d","discovery_id":"1","validation":"DISCOVERY_ONLY"}])
    assert result["total"] is False
    assert "UNRESOLVED_DISCOVERIES:1" in result["blockers"]


def test_discovery_source_failure_does_not_block_coverage():
    from src.poll_monitor import PollMonitor
    monitor = PollMonitor.__new__(PollMonitor)
    monitor.config = {"coverage_contract":{"scope":"configured_national_poll_universe"},
                      "sources":[
                          {"id":"primary","coverage_role":"primary","format":"national_html"},
                          {"id":"discovery","coverage_role":"discovery","format":"page"},
                      ]}
    monitor.state = {"source_status":{
        "primary":{"status":"OK"},
        "discovery":{"status":"FAILED"},
    }}
    result = monitor.audit_coverage([{"source_id":"discovery","error":"HTTP 400"}], [])
    assert result["total"] is True
    assert "SOURCE_NOT_HEALTHY:discovery" not in result["blockers"]


def test_config_uses_current_known_source_endpoints():
    cfg=json.loads(Path("config/poll_monitor.json").read_text())
    by_id={s["id"]: s for s in cfg["sources"]}
    assert by_id["electomania_ajax"]["url"] == "https://electomania.es/encuestas/"
    assert by_id["sigma_dos"]["url"] == "https://www.sigmados.com/"
    assert by_id["elpais_40db"]["url"] == "https://elpais.com/noticias/encuestas-electorales/"
    assert by_id["myfdata"]["disabled"] is True
    assert by_id["myfdata"]["coverage_role"] == "discovery"

def test_workflow_has_json_preflight():
    workflow = Path(".github/workflows/poll_monitor.yml").read_text()
    assert "python -m json.tool config/poll_monitor.json" in workflow


def test_workflow_does_not_self_trigger_and_retries_non_fast_forward():
    workflow = Path(".github/workflows/poll_monitor.yml").read_text()
    assert "paths-ignore:" in workflow
    assert '"artifacts/**"' in workflow
    assert "git fetch origin main" in workflow
    assert "git reset --hard origin/main" in workflow
    assert "python -m src.poll_monitor" in workflow
    assert "for attempt in 1 2 3 4 5" in workflow
