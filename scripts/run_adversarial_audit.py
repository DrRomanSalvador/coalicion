#!/usr/bin/env python3
"""Adversarial first-party audit of COALICIÓN certification evidence.

This audit is deliberately separate from the master certification logic, but it
is NOT an independent external audit. It must never be used to satisfy the
external_audit gate.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read_json(path):
    p = ROOT / path
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None

def main():
    checks = []

    manifest = read_json("ci_evidence/historico_manifest.json")
    interior = read_json("ci_evidence/interior_acquisition.json")
    checks.append({
        "id": "PRIMARY_INTERIOR",
        "pass": bool(
            isinstance(manifest, dict)
            and manifest.get("status") in {"PASS", "CERTIFIED"}
            and manifest.get("source_tier") == "PRIMARY_INTERIOR"
        ),
        "evidence": "ci_evidence/historico_manifest.json",
    })
    checks.append({
        "id": "INTERIOR_ACQUISITION",
        "pass": bool(
            isinstance(interior, dict)
            and interior.get("status") == "PASS"
            and interior.get("n_rows") == 50700
            and interior.get("n_constituencies_per_election") == 52
            and interior.get("seats_per_election") == 350
        ),
        "evidence": "ci_evidence/interior_acquisition.json",
    })

    oos_input = ROOT / "data/encuestas_historicas_2004_2023.csv"
    oos = read_json("ci_evidence/oos_calibration.json")
    checks.append({
        "id": "OOS_INPUT",
        "pass": oos_input.exists() and oos_input.stat().st_size > 0,
        "evidence": str(oos_input.relative_to(ROOT)),
    })
    checks.append({
        "id": "OOS_CALIBRATION",
        "pass": bool(
            isinstance(oos, dict)
            and oos.get("status") in {"PASS", "CERTIFIED"}
            and int(oos.get("n_rows", 0)) > 0
            and int(oos.get("n_elections", 0)) >= 3
            and int(oos.get("walk_forward_holdouts", 0)) >= 1
            and oos.get("leakage_checks", {}).get("field_end_before_election") is True
            and oos.get("leakage_checks", {}).get("all_test_elections_use_only_prior_elections") is True
        ),
        "evidence": "ci_evidence/oos_calibration.json",
    })

    posterior = read_json("ci_evidence/seec_posterior.json") or read_json("ci_evidence/seec_production.json")
    draws = int(posterior.get("total_posterior_draws", posterior.get("draws", 0))) if isinstance(posterior, dict) else 0
    checks.append({
        "id": "SEEC_10000",
        "pass": bool(isinstance(posterior, dict) and posterior.get("status") in {"PASS", "CERTIFIED"} and draws >= 10000),
        "evidence": "ci_evidence/seec_posterior.json",
        "draws": draws,
    })

    backtest = read_json("artifacts/verification/full_backtest.json")
    checks.append({
        "id": "FULL_BACKTEST",
        "pass": bool(isinstance(backtest, dict) and backtest.get("status") == "PASS"),
        "evidence": "artifacts/verification/full_backtest.json",
    })

    external = read_json("ci_evidence/external_audit.json")
    checks.append({
        "id": "EXTERNAL_AUDIT",
        "pass": bool(
            isinstance(external, dict)
            and external.get("status") in {"PASS", "CERTIFIED"}
            and external.get("independent") is True
            and bool(external.get("auditor"))
        ),
        "evidence": "ci_evidence/external_audit.json",
        "note": "This check can only pass from genuinely independent evidence.",
    })

    passed = sum(1 for c in checks if c["pass"])
    failed = [c["id"] for c in checks if not c["pass"]]
    out = {
        "schema": "ADVERSARIAL_FIRST_PARTY_AUDIT_V1",
        "status": "PASS" if not failed else "FAIL",
        "independent": False,
        "auditor": "COALICION_INTERNAL_ADVERSARIAL_REVIEW",
        "scope": "certification evidence, reproducibility gates, temporal leakage controls and external-audit integrity",
        "checks_total": len(checks),
        "checks_passed": passed,
        "checks_failed": len(failed),
        "failed_checks": failed,
        "checks": checks,
        "critical_rule": "This artifact MUST NOT satisfy master_certification.external_audit.",
    }
    p = ROOT / "ci_evidence/adversarial_first_party_audit.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    raise SystemExit(0 if not failed else 1)

if __name__ == "__main__":
    main()
