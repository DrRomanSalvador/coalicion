from src.alerts.situation_alerts import build_publishable_alerts


def test_small_change_is_suppressed():
    state = {
        "policy": {"fail_closed": True, "descriptive_only": True},
        "headline": {"changed": [{"type": "poll_observation_change", "party": "A", "delta_pp": 0.9}]},
    }
    assert build_publishable_alerts(state) == []


def test_material_change_is_one_line_and_evidence_backed():
    state = {
        "policy": {"fail_closed": True, "descriptive_only": True},
        "headline": {"changed": [{
            "type": "poll_observation_change",
            "party": "A",
            "delta_pp": 1.2,
            "evidence": ["https://example.invalid/source"],
        }]},
    }
    alerts = build_publishable_alerts(state)
    assert len(alerts) == 1
    assert "A" in alerts[0]["message"]
    assert alerts[0]["evidence"]
