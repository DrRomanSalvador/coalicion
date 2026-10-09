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

def test_source_tier_requires_explicit_registry_and_is_applied():
    from src.poll_monitor import apply_source_tier
    poll = valid_poll()
    assert apply_source_tier([poll], {"id": "unknown"})[0].source_tier == "SECONDARY_REPLICA"
    assert apply_source_tier([poll], {"id": "direct", "source_tier": "PRIMARY_POLLSTER"})[0].source_tier == "PRIMARY_POLLSTER"
    assert apply_source_tier([poll], {"id": "mirror", "source_tier": "SECONDARY_REPLICA"})[0].source_tier == "SECONDARY_REPLICA"

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
    assert by_id["lasexta_invymark_discovery"]["coverage_role"] == "discovery"
    assert by_id["lasexta_invymark_discovery"]["source_tier"] == "SECONDARY_REPLICA"


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


def test_workflow_does_not_self_trigger_and_persists_with_self_healing():
    workflow = Path(".github/workflows/poll_monitor.yml").read_text()
    assert "paths-ignore:" in workflow
    assert '"artifacts/**"' in workflow
    assert "git fetch origin main" in workflow
    assert "git reset --hard origin/main" in workflow
    assert "python -m src.poll_monitor" in workflow
    assert "/tmp/poll-monitor-snapshot" in workflow
    assert "cp /tmp/poll-monitor-snapshot/poll_monitor_state.json" in workflow
    assert "cp /tmp/poll-monitor-snapshot/survey_history.jsonl" in workflow
    assert "for attempt in 1 2 3 4 5" in workflow
    assert "git rebase" not in workflow


def test_canonical_electoral_source_registry():
    cfg = json.loads(Path("config/electoral_sources.json").read_text(encoding="utf-8"))
    assert cfg["scope"] == "Spain"
    assert cfg["data_policy"]["primary_source_precedence"] is True
    assert cfg["data_policy"]["no_synthetic_values"] is True
    assert any(s["id"] == "interior" and s["role"] == "primary_official" for s in cfg["official_results"])
    assert any(s["id"] == "cis" and s["role"] == "primary_official" for s in cfg["official_surveys"])
    all_sources = cfg["official_results"] + cfg["official_surveys"] + cfg["private_pollsters"] + cfg["aggregators_discovery"]
    assert len({s["id"] for s in all_sources}) == len(all_sources)
    assert any(s["id"] == "sigma_dos" and "EL MUNDO" in s["publication_media"] for s in cfg["private_pollsters"])
    assert cfg["election_scope_correction"]["general_elections_2023"] == "2023-07-23"
    assert cfg["election_scope_correction"]["invalid_claim_rejected"] == "2023-11-23"


def test_oos_selection_excludes_latest_holdout(monkeypatch):
    from src import oos_pipeline
    from src.poll_error import PollObservation

    rows = [
        PollObservation("2004", "2004-03-14", "PSOE", 40.0, 42.0, "Congreso", "2004-03-01", "CIS", "a"),
        PollObservation("2008", "2008-03-09", "PSOE", 43.0, 44.0, "Congreso", "2008-03-01", "CIS", "b"),
        PollObservation("2023J", "2023-07-23", "PSOE", 28.0, 31.0, "Congreso", "2023-07-01", "CIS", "c"),
    ]
    seen = {}
    original_bias = oos_pipeline.select_best
    original_context = oos_pipeline.select

    def capture_bias(training):
        seen["bias"] = list(training)
        return original_bias(training)

    def capture_context(training):
        seen["context"] = list(training)
        return original_context(training)

    monkeypatch.setattr(oos_pipeline, "select_best", capture_bias)
    monkeypatch.setattr(oos_pipeline, "select", capture_context)
    result = oos_pipeline.run_oos(rows)

    assert result["holdout_election"] == "2023J"
    assert all(r.election != "2023J" for r in seen["bias"])
    assert all(r.election != "2023J" for r in seen["context"])
    assert result["holdout_rows"] == 1
    assert result["contract"] == "EXPANDING_WINDOW_NO_FUTURE_LEAKAGE"


def test_oos_rejects_poll_on_or_after_target_election():
    from src import oos_pipeline
    from src.poll_error import PollObservation

    rows = [
        PollObservation("2004", "2004-03-14", "PSOE", 40.0, 42.0, "Congreso", "2004-03-14", "CIS", "bad"),
        PollObservation("2008", "2008-03-09", "PSOE", 43.0, 44.0, "Congreso", "2008-03-01", "CIS", "ok"),
    ]
    import pytest
    with pytest.raises(ValueError, match="future leakage"):
        oos_pipeline.run_oos(rows)


def test_historical_validator_uses_certified_official_row_floor():
    source = Path("scripts/validate_historical_data.py").read_text(encoding="utf-8")
    assert 'EXPECTED_ROWS = 50700' in source
    assert 'seats.is_integer()' in source



def test_named_adapters_import_and_validate():
    from src.monitors import CISMonitor, ElectomaniaMonitor, DatoElectoralMonitor, TwitterMonitor
    from src.poll_validator import validate_poll as public_validate
    from src.poll_hasher import poll_hash as public_hash, poll_identity as public_identity
    from src.poll_normalizer import normalize_party_name as public_normalize
    poll = valid_poll()
    assert public_validate(poll)[0] is True
    assert public_hash(poll) == poll_hash(poll)
    assert public_identity(poll) == poll_identity(poll)
    assert public_normalize("Partido Popular") == "PP"
    assert all(cls is not None for cls in (CISMonitor, ElectomaniaMonitor, DatoElectoralMonitor, TwitterMonitor))


def test_telegram_notifier_fails_closed_without_token(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    from src.telegram_notifier import resolve_private_chat, send_message
    assert resolve_private_chat() is None
    assert send_message("test") is False


def test_electomania_public_html_adapter_extracts_explicit_table():
    html = b"""<html><head><title>Encuesta Demo</title></head><body>
    <h1>Sondeo para elecciones generales</h1>
    <p>01/10/2026</p><p>Partido | Voto (%) | Escanos</p>
    <p>PP 33,8% PSOE 25,9% VOX 18,8% Sumar 5,9% Podemos 3,8% ERC 2,0%</p>
    </body></html>"""
    from src.monitors.electomania_monitor import ElectomaniaMonitor
    import requests
    polls, discoveries = ElectomaniaMonitor({"id":"electomania","url":"https://example.test","pollster":"Demo"}, requests.Session()).parse(html)
    assert len(polls) == 1
    assert polls[0].publication_date == "2026-10-01"
    assert polls[0].parties["PP"] == 33.8
    assert discoveries == []

def test_poll_monitor_migrates_v2_state_schema(tmp_path):
    from src.poll_monitor import PollMonitor
    state = tmp_path / "state.json"
    state.write_text(json.dumps({"schema":"POLL_MONITOR_STATE_V2","poll_hashes":{"x":"h"}}), encoding="utf-8")
    monitor = PollMonitor.__new__(PollMonitor)
    monitor.state_path = state
    loaded = monitor._load_state()
    assert loaded["schema"] == "POLL_MONITOR_STATE_V3"
    assert loaded["poll_hashes"] == {"x":"h"}


def test_poll_monitor_versions_corrections(tmp_path):
    from src.poll_monitor import PollMonitor, Poll
    monitor = PollMonitor.__new__(PollMonitor)
    monitor.state_path = tmp_path / "state.json"
    monitor.state = {"poll_hashes": {}, "poll_identities": {}, "discovery_hashes": {}}
    poll = Poll("p1", "2026-10-07", "House", "s1", "https://example.test", {"PP": 35, "PSOE": 30, "VOX": 10, "SUMAR": 8, "PODEMOS": 5})
    new, changed, _ = monitor.detect_new([poll], [])
    assert new[0]["event_type"] == "NEW"
    poll2 = Poll("p1", "2026-10-07", "House", "s1", "https://example.test", {"PP": 36, "PSOE": 29, "VOX": 10, "SUMAR": 8, "PODEMOS": 5})
    new, changed, _ = monitor.detect_new([poll2], [])
    assert changed[0]["event_type"] == "CORRECTION_OR_REPUBLICATION"
    assert len(monitor.state["poll_versions"]["p1"]) == 2


def test_oos_reports_full_expanding_window_walk_forward():
    from src import oos_pipeline
    from src.poll_error import PollObservation

    rows = []
    elections = [
        ("2004", "2004-03-14", "2004-03-01"),
        ("2008", "2008-03-09", "2008-03-01"),
        ("2011", "2011-11-20", "2011-11-01"),
    ]
    for election, election_date, field_end in elections:
        rows.append(PollObservation(election, election_date, "PSOE", 40.0, 42.0,
                                    "Congreso", field_end, "CIS", election))
    result = oos_pipeline.run_oos(rows)
    assert result["walk_forward_contract"] == "ALL_TEST_ELECTIONS_USE_ONLY_PRIOR_ELECTIONS"
    assert result["walk_forward_holdouts"] == 1
    assert result["walk_forward"][0]["election"] == "2011"
    assert result["walk_forward"][0]["training_elections"] == ["2004", "2008"]


def test_context_correction_learns_government_from_training_rows():
    from src.context_corrections import predict
    from src.poll_error import PollObservation

    train = [
        PollObservation("2004", "2004-03-14", "PSOE", 30.0, 35.0, "Congreso", "2004-03-01", "CIS",
                        "a", governing_party="PP"),
        PollObservation("2008", "2008-03-09", "PP", 30.0, 35.0, "Congreso", "2008-03-01", "CIS",
                        "b", governing_party="PP"),
        PollObservation("2011", "2011-11-20", "PSOE", 30.0, 25.0, "Congreso", "2011-11-01", "CIS",
                        "c", governing_party="PSOE"),
    ]
    target = PollObservation("2015", "2015-12-20", "PSOE", 30.0, 30.0, "Congreso",
                             "2015-12-01", "CIS", "d", governing_party="PP")
    # PP-government rows have +5/+5 training bias; PSOE-government has -5.
    assert predict("GOVERNMENT", train, target) > 30.0

def test_source_fingerprint_ignores_volatile_html_but_tracks_visible_text():
    from src.poll_monitor import source_content_fingerprint, SourceMonitor
    source = {"id": "page", "url": "https://example.test", "format": "page", "name": "Example"}
    first = b'<html><script>const id="abc";</script><div id="x1">Same visible text</div></html>'
    volatile = b'<html><script>const id="xyz";</script><div id="x2">Same   visible text</div></html>'
    changed = b'<html><script>const id="xyz";</script><div id="x2">New visible text</div></html>'
    assert source_content_fingerprint(first, source) == source_content_fingerprint(volatile, source)
    assert source_content_fingerprint(first, source) != source_content_fingerprint(changed, source)

    class FakeSession:
        pass
    monitor = SourceMonitor(source, FakeSession())
    _, d1 = monitor.parse(first)
    _, d2 = monitor.parse(volatile)
    _, d3 = monitor.parse(changed)
    assert d1[0]["discovery_id"] == d2[0]["discovery_id"] == d3[0]["discovery_id"]
    assert d1[0]["source_hash"] == d2[0]["source_hash"]
    assert d1[0]["source_hash"] != d3[0]["source_hash"]

