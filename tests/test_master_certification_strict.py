import json\nfrom scripts.master_certification import certify\n\ndef test_present_but_invalid_evidence_cannot_certify(tmp_path):\n    d=tmp_path / "ci_evidence"\n    d.mkdir()\n    (d / "historico_manifest.json").write_text(json.dumps({"status":"FAIL","source_tier":"SECONDARY_REPLICA"}))\n    (d / "historico_source_tier.txt").write_text("PRIMARY_INTERIOR")\n    (d / "reconciliation.json").write_text(json.dumps({"status":"PASS","max_abs_diff":1722}))\n    (d / "seec_posterior.json").write_text(json.dumps({"status":"PASS","draws":10000}))\n    (d / "oos_calibration.json").write_text(json.dumps({"status":"PASS","coverage_90":0.90,"seat_mae":5}))\n    (d / "external_audit.json").write_text(json.dumps({"status":"PASS","independent":False,"auditor":""}))\n    out=certify(tmp_path)\n    assert out["status"]=="PENDING_REQUEST"\n    assert any(g["name"]=="reconciliation" and g["status"]=="FAIL" for g in out["gates"])\n    assert any(g["name"]=="external_audit" and g["status"]=="FAIL" for g in out["gates"])\n

def test_request_never_certifies_and_invalid_approval_never_certifies(tmp_path):
    d=tmp_path / "ci_evidence"
    d.mkdir()
    (d / "historico_manifest.json").write_text(json.dumps({"status":"FAIL","source_tier":"SECONDARY_REPLICA"}))
    (d / "historico_source_tier.txt").write_text("PRIMARY_INTERIOR")
    (d / "reconciliation.json").write_text(json.dumps({"status":"PASS","max_abs_diff":1722}))
    (d / "seec_posterior.json").write_text(json.dumps({"status":"PASS","draws":10000}))
    (d / "oos_calibration.json").write_text(json.dumps({"status":"PASS","coverage_90":0.90,"seat_mae":5}))
    (d / "external_audit.json").write_text(json.dumps({"status":"PASS","independent":False,"auditor":""}))
    (d / "certification_request.json").write_text(json.dumps({
        "schema":"CERTIFICATION_REQUEST_V1","status":"PENDING_APPROVAL",
        "approval_required":True,"approved":False
    }))
    (d / "certification_approval.json").write_text(json.dumps({
        "schema":"CERTIFICATION_APPROVAL_V1","decision":"CERTIFY","approved":True,
        "approved_by":"invalid","approved_at":"2026-10-07T00:00:00Z","evidence_digest":"wrong"
    }))
    out=certify(tmp_path)
    assert out["status"]=="PENDING_APPROVAL"
    assert out["certification_request"] is True
    assert out["certification_approval"] is False
    assert out["eligible_for_approval"] is False
