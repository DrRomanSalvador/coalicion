from src.alerts.realtime_notifier import build_alerts

def test_new_poll_and_source_failure_are_explicit_events():
    current={"poll_hashes":{"p":"new"},"sources":{"a":"FAILED"}}
    previous={"poll_hashes":{},"sources":{"a":"OK"}}
    events=build_alerts(current, previous)
    assert [e["category"] for e in events] == ["new_poll","source_failure"]

def test_source_recovery_requires_previous_failure():
    current={"sources":{"a":"OK","b":"OK"}}
    previous={"sources":{"a":"FAILED","b":"OK"}}
    events=build_alerts(current, previous)
    assert events == [{"category":"source_recovery","key":"a:FAILED->OK","detail":"a: recuperada."}]
