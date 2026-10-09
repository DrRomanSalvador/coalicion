import json

from scripts.master_certification import certify


def test_present_but_invalid_evidence_cannot_certify(tmp_path):
    d = tmp_path / "ci_evidence"
    d.mkdir()
    (d / "historico_manifest.json").write_text(
        json.dumps({"status": "FAIL", "source_tier": "SECONDARY_REPLICA"})
    )
    (d / "historico_source_tier.txt").write_text("PRIMARY_INTERIOR")
    (d / "reconciliation.json").write_text(
        json.dumps({"status": "PASS", "max_abs_diff": 1722})
    )
    (d / "seec_posterior.json").write_text(
        json.dumps({"status": "PASS", "draws": 10000})
    )
    (d / "oos_calibration.json").write_text(
        json.dumps({"status": "PASS", "coverage_90": 0.90, "seat_mae": 5})
    )
    (d / "external_audit.json").write_text(
        json.dumps({"status": "PASS", "independent": False, "auditor": ""})
    )

    out = certify(tmp_path)

    assert out["status"] == "BLOCKED"
    assert any(
        g["name"] == "reconciliation" and g["status"] == "FAIL"
        for g in out["gates"]
    )
    assert any(
        g["name"] == "external_audit" and g["status"] == "FAIL"
        for g in out["gates"]
    )
    assert any(
        g["name"] == "official_workbook_dataset" and g["status"] == "FAIL"
        for g in out["gates"]
    )
