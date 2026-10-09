def test_certification_evidence_is_bound_to_exact_github_commit(monkeypatch, tmp_path):
    from scripts.master_certification import certify

    monkeypatch.setenv("GITHUB_SHA", "abc123")
    monkeypatch.setenv("GITHUB_REF", "refs/heads/main")
    result = certify(str(tmp_path))
    assert result["tested_commit"] == "abc123"
    assert result["tested_ref"] == "refs/heads/main"
    assert result["evidence_sha256"] == {}
    assert result["fail_closed"] is True


from scripts.master_certification import certify

def test_master_certification_fails_closed_on_missing_evidence(tmp_path):
    out=certify(tmp_path)
    assert out["status"]=="BLOCKED"
    assert all(g["status"]=="FAIL" for g in out["gates"] if g["name"] in {
        "source_manifest","primary_interior","reconciliation","seec_posterior",
        "mc_10000","oos_calibration","coverage_90","seat_mae","external_audit"})
