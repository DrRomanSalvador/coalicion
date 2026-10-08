import pytest
from src.recovery.retry_fallback import retry

def test_retry_succeeds_before_exhaustion():
    calls={"n":0}
    def fetch():
        calls["n"] += 1
        if calls["n"] < 2:
            raise OSError("temporary")
        return "ok"
    assert retry(fetch, attempts=3) == "ok"
    assert calls["n"] == 2

def test_retry_fails_closed_without_fallback():
    with pytest.raises(RuntimeError, match="BLOCKED_SOURCE_FETCH_AFTER_RETRIES"):
        retry(lambda: (_ for _ in ()).throw(OSError("down")), attempts=2)

def test_fallback_is_explicit():
    assert retry(lambda: (_ for _ in ()).throw(OSError("down")), attempts=2, fallback=lambda:"fallback") == "fallback"
