from src.political_intelligence import component_status, intelligence_snapshot

def test_component_contract_exposes_canonical_stack():
    status = component_status()
    assert status["components"]["electoral_engine"]["state"] == "PRESENT"
    assert status["components"]["prediction"]["state"] == "PRESENT"
    assert status["components"]["oos"]["state"] == "PRESENT"
    assert status["components"]["calibration"]["state"] == "PRESENT"
    assert status["components"]["decision"]["state"] == "PRESENT"

def test_intelligence_snapshot_is_fail_closed_and_neutral():
    snapshot = intelligence_snapshot(as_of="2026-10-08")
    assert snapshot["policy"]["neutral"] is True
    assert snapshot["policy"]["no_hidden_imputation"] is True
    assert snapshot["policy"]["no_certification_without_evidence"] is True
    assert snapshot["gates"]["registry"] is True
    assert snapshot["gates"]["fail_closed"] is True
    assert snapshot["status"] in {"BLOCKED", "READY_FOR_EXECUTION"}
