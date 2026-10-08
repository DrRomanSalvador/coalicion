from src.poll_ingest import Poll as IngestPoll, poll_hash as ingest_poll_hash
from src.poll_monitor import Poll as MonitorPoll, poll_hash as monitor_poll_hash

def test_poll_ingestion_uses_canonical_contract():
    assert IngestPoll is MonitorPoll
    poll = IngestPoll(
        "p", "2026-10-07", "Demo", "x", "https://example.test",
        {"PP": 30.0, "PSOE": 28.0, "VOX": 18.0, "SUMAR": 6.0, "PODEMOS": 4.0},
    )
    assert ingest_poll_hash(poll) == monitor_poll_hash(poll)
