from src.monitors.cis_monitor import CISMonitor

def test_cis_rss_is_discovery_only():
    rss=b"<rss><channel><item><title>Barometro</title><link>https://example.test/p</link><guid>p</guid></item></channel></rss>"
    polls, discoveries=CISMonitor({"id":"cis","url":"https://example.test"}, None).parse(rss)
    assert polls == []
    assert discoveries[0]["validation"] == "DISCOVERY_ONLY"
