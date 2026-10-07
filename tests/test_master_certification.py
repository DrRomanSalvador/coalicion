from scripts.master_certification import certify

def test_master_certification_fails_closed_on_missing_evidence(tmp_path):
    out=certify(tmp_path)
    assert out["status"]=="PENDING_REQUEST"
    assert all(g["status"]=="FAIL" for g in out["gates"] if g["name"] in {
        "source_manifest","primary_interior","reconciliation","seec_posterior",
        "mc_10000","oos_calibration","coverage_90","seat_mae","external_audit"})
