from scripts.product_status import product_status

def test_product_reports_sellable_beta_without_overclaiming_prediction_certification():
    s=product_status(".")
    assert s["status"]=="SELLABLE_BETA"
    assert s["certification"]=="READY_FOR_EXTERNAL_AUDIT"
    assert s["use_allowed"] is True
    assert s["data_source"]=="PRIMARY_INTERIOR_WORKBOOK"
    assert s["prediction_status"]=="BLOCKED_NO_VALIDATED_52_CONSTITUENCY_2026_MATRIX"
    assert s["evidence"]["historical_elections"]==16
    assert s["evidence"]["constituencies"]==52
    assert s["evidence"]["seat_reconciliation"]["discrepancies"]==0
