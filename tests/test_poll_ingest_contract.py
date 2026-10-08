from src.poll_ingest import Poll as IngestPoll, poll_hash as ingest_poll_hash
from src.poll_monitor import Poll as MonitorPoll, poll_hash as monitor_poll_hash

def test_poll_ingestion_uses_canonical_contract():
    assert IngestPoll is MonitorPoll
    poll = IngestPoll(
        "p", "2026-10-07", "Demo", "x", "https://example.test",
        {"PP": 30.0, "PSOE": 28.0, "VOX": 18.0, "SUMAR": 6.0, "PODEMOS": 4.0},
    )
    assert ingest_poll_hash(poll) == monitor_poll_hash(poll)

def test_capture_metadata_does_not_change_poll_identity_hash():
    base = MonitorPoll(
        "p", "2026-10-07", "Demo", "x", "https://example.test",
        {"PP": 30.0, "PSOE": 28.0, "VOX": 18.0, "SUMAR": 6.0, "PODEMOS": 4.0},
        captured_at="2026-10-08T00:00:00+00:00",
        source_content_hash="a" * 64,
    )
    recaptured = MonitorPoll(
        **{**base.__dict__, "captured_at": "2026-10-08T00:30:00+00:00", "source_content_hash": "b" * 64}
    )
    assert monitor_poll_hash(base) == monitor_poll_hash(recaptured)
