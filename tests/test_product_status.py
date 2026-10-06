from scripts.product_status import product_status

def test_secondary_evidence_can_enable_beta():
    s=product_status(".")
    assert s["status"]=="OPERATIONAL_BETA"
    assert s["certification"]=="PARTIAL"
    assert s["use_allowed"] is True
    assert s["evidence"]["validation_status"]=="PASS"
    assert s["evidence"]["arithmetic_bad_cells"]==0
    assert len(s["warnings"])>=2
