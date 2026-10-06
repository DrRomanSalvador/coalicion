from src.operational_status import get_status

def test_secondary_replica_enables_beta_without_strict_certification():
    s=get_status(".")
    assert s["mode"] in {"OPERATIONAL_BETA","OPERATIONAL","BLOCKED"}
    if s["data_source"]=="SECONDARY_REPLICA_VERIFIED":
        assert s["mode"]=="OPERATIONAL_BETA"
        assert s["certification"]=="PARTIAL"
        assert s["use_allowed"] is True
        assert s["warnings"]
