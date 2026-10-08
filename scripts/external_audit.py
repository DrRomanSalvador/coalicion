"""Fail-closed technical audit of underlying COALICIÓN evidence.

This does not claim third-party independence and does not trust the master
certification status as evidence for the technical gates.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

def read_json(path: str):
    try:
        return json.loads((ROOT / path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

def sha256(path: str):
    try:
        return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
    except OSError:
        return None

def gate(name, ok, detail):
    return {"name": name, "status": "PASS" if ok else "FAIL", "detail": detail}

def main():
    checks = []

    oos = read_json("ci_evidence/oos_calibration.json")
    checks.append(gate("OOS", isinstance(oos, dict) and oos.get("status") == "PASS"
        and float(oos.get("coverage_gate", {}).get("observed_base_mean_coverage", 0)) >= .85
        and oos.get("coverage_gate", {}).get("passed") is True
        and all(oos.get("leakage_checks", {}).values()), "coverage + leakage"))

    mc = read_json("ci_evidence/mc_10000.json")
    checks.append(gate("MC_10000", isinstance(mc, dict) and mc.get("status") == "PASS"
        and int(mc.get("iterations", 0)) >= 10000 and int(mc.get("constituencies", 0)) == 52
        and int(mc.get("seats", 0)) == 350
        and mc.get("invariants", {}).get("every_draw_seat_sum_350") is True
        and mc.get("invariants", {}).get("all_allocations_status_OK") is True, "10,000 draws + 350-seat invariant"))

    seec = read_json("ci_evidence/seec_production.json")
    d = seec.get("diagnostics", {}) if isinstance(seec, dict) else {}
    checks.append(gate("SEEC_PYMC", isinstance(seec, dict) and seec.get("status") == "PASS"
        and int(seec.get("total_draws", 0)) >= 10000 and int(seec.get("chains", 0)) >= 4
        and int(d.get("divergences", 1)) == 0 and float(d.get("max_r_hat", 99)) <= 1.01
        and float(d.get("min_ess_bulk", 0)) >= 1000 and float(d.get("min_ess_tail", 0)) >= 1000
        and seec.get("convergence", {}).get("passed") is True, "PyMC/NUTS convergence"))

    bt = read_json("ci_evidence/backtest_2023_baseline.json")
    c = bt.get("contracts", {}) if isinstance(bt, dict) else {}
    required = ("historical_conformal_calibration","calibration_before_target_election",
        "target_election_excluded_from_calibration","conformal_nominal_coverage_95",
        "family_level_calibration","party_specific_calibration","calibrated_coverage_gate",
        "no_future_vote_input","canonical_electoral_engine","seat_sum_350")
    checks.append(gate("BACKTEST_2023", isinstance(bt, dict) and bt.get("schema") == "BACKTEST_2023_BASELINE_V3"
        and bt.get("status") == "PASS" and int(bt.get("n_simulations", 0)) >= 10000
        and bt.get("source_tier") == "PRIMARY_OFFICIAL"
        and float(bt.get("metrics", {}).get("coverage_actual_seats_in_calibrated_interval_winners", 0)) >= .85
        and all(c.get(k) is True for k in required), "territorial calibration + leakage contracts"))

    complete = read_json("ci_evidence/backtest_complete_2004_2023.json")
    checks.append(gate("COMPLETE_BACKTEST", isinstance(complete, dict) and complete.get("status") == "PASS"
        and complete.get("oos", {}).get("status") == "PASS"
        and float(complete.get("oos", {}).get("coverage", 0)) >= .85, "historical OOS"))

    polls = read_json("ci_evidence/poll_source_coverage.json")
    r = polls.get("last_runtime_coverage", {}) if isinstance(polls, dict) else {}
    checks.append(gate("POLL_COVERAGE", isinstance(polls, dict) and polls.get("status") == "PASS"
        and int(polls.get("primary_sources", 0)) == int(polls.get("healthy_primary_sources", -1))
        and r.get("total") is True and r.get("blockers") == [], "primary-source coverage"))

    checks.append(gate("EVIDENCE_PRESENT",
        all(sha256(p) for p in (
            "ci_evidence/oos_calibration.json","ci_evidence/mc_10000.json",
            "ci_evidence/seec_production.json","ci_evidence/backtest_2023_baseline.json",
            "ci_evidence/backtest_complete_2004_2023.json","ci_evidence/poll_source_coverage.json")),
        "all critical evidence files present and hashable"))

    master = read_json("ci_evidence/master_certification.json")
    checks.append(gate("MASTER_REPORTED_STATE",
        isinstance(master, dict) and master.get("status") == "READY_FOR_EXTERNAL_AUDIT",
        "reported only; not trusted for technical gate results"))

    failed = [x for x in checks if x["status"] != "PASS"]
    result = {
        "schema": "EXTERNAL_TECHNICAL_AUDIT_V1",
        "verdict": "PASS" if not failed else "FAIL",
        "independence": "NOT_CLAIMED",
        "mode": "DEMONSTRATION_NON_OFFICIAL",
        "demo_validation": "ACCEPTED_FOR_DEMONSTRATION_ONLY",
        "checks": checks,
        "fail_closed": True,
        "required_next_step": "THIRD_PARTY_SIGNOFF",
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if not failed else 1

if __name__ == "__main__":
    raise SystemExit(main())
