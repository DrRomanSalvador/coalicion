from scripts.product_status import product_status

def test_product_remains_blocked_without_full_primary_certificate():
    s=product_status(".")
    assert s["status"]=="BLOCKED"
    assert s["certification"]=="BLOCKED"
    assert s["use_allowed"] is False
