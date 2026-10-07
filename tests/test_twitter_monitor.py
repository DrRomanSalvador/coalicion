def test_twitter_monitor_requires_credentials():
    import os
    from src.monitors.twitter_monitor import TwitterMonitor
    os.environ.pop("X_BEARER_TOKEN", None)
    monitor=TwitterMonitor({"id":"x","url":"https://api.twitter.com/2/users/{user_id}/tweets","user_id":""}, None)
    try:
        monitor.fetch()
    except RuntimeError as exc:
        assert "X_BEARER_TOKEN_NOT_CONFIGURED" in str(exc)
    else:
        raise AssertionError("missing X credentials must fail closed")
