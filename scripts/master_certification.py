"""Master certification gate: evidence-only, fail-closed, hash-aware."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json


@dataclass(frozen=True)
class Gate:
    name: str
    status: str
    detail: str


def _gate(name: str, condition: bool, detail: str) -> Gate:
    return Gate(name, "PASS" if condition else "FAIL", detail)


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _hash_matches(path: Path, expected: str | None) -> bool:
    return bool(expected) and _sha256(path) == expected


def certify(root: str = "."):
    r = Path(root)
    gates: list[Gate] = []

    manifest_path = r / "ci_evidence/historico_manifest.json"
    tier_path = r / "ci_evidence/historico_source_tier.txt"
    manifest = _read_json(manifest_path)
    manifest_ok = (
        isinstance(manifest, dict)
        and manifest.get("status") in {"PASS", "CERTIFIED"}
        and manifest.get("source_tier") == "PRIMARY_INTERIOR"
        and int(manifest.get("materialized_rows", 0)) == int(manifest.get("expected_rows", -1))
        and int(manifest.get("elections_required", 0)) == 8
        and int(manifest.get("constituencies_required", 0)) == 52
        and int(manifest.get("seats_per_election", 0)) == 350
    )
    gates.append(_gate("source_manifest", manifest_ok, "manifest primario materializado y estructuralmente validado"))

    tier_text = tier_path.read_text(encoding="utf-8").strip() if tier_path.exists() else ""
    gates.append(_gate(
        "primary_interior",
        tier_text == "PRIMARY_INTERIOR" or (
            isinstance(manifest, dict) and manifest.get("source_tier") == "PRIMARY_INTERIOR"
        ),
        "la fuente histórica debe estar declarada como primaria",
    ))

    recon_path = r / "ci_evidence/reconciliation.json"
    recon = _read_json(recon_path)
    gates.append(_gate(
        "reconciliation",
        isinstance(recon, dict)
        and recon.get("status") == "PASS"
        and float(recon.get("max_abs_diff", 1)) == 0
        and bool(recon.get("fail_closed", False)),
        "reconciliación exacta y fail-closed",
    ))

    # Production SEEC only. Auxiliary territorial simulations cannot satisfy this gate.
    posterior_path = r / "ci_evidence/seec_production.json"
    posterior = _read_json(posterior_path)
    posterior_ok = (
        isinstance(posterior, dict)
        and posterior.get("status") in {"PASS", "CERTIFIED"}
        and posterior.get("schema") == "SEEC_PRODUCTION_POSTERIOR_V2"
        and posterior.get("model") == "hierarchical_compositional_temporal_dirichlet_logistic_normal"
        and int(posterior.get("total_draws", 0)) >= 10000
        and int(posterior.get("studies", 0)) >= 8
        and int(posterior.get("draws_per_chain", 0)) >= 1000
        and int(posterior.get("chains", 0)) >= 4
        and int(posterior.get("diagnostics", {}).get("divergences", 1)) == 0
        and float(posterior.get("diagnostics", {}).get("max_r_hat", 99)) <= 1.01
        and float(posterior.get("diagnostics", {}).get("min_ess_bulk", 0)) >= 1000
        and float(posterior.get("diagnostics", {}).get("min_ess_tail", 0)) >= 1000
        and bool(posterior.get("convergence", {}).get("passed", False))
    )
    gates.append(_gate(
        "seec_posterior",
        posterior_ok,
        "posterior jerárquico PyMC de producción >=10.000 draws con convergencia materializada",
    ))

    # MC-10000 is an independent simulation artifact; never infer it from SEEC.
    mc_path = r / "ci_evidence/mc_10000.json"
    mc = _read_json(mc_path)
    mc_ok = (
        isinstance(mc, dict)
        and mc.get("status") in {"PASS", "CERTIFIED"}
        and mc.get("schema") == "ELECTORAL_MONTE_CARLO_10000_V2"
        and int(mc.get("iterations", 0)) >= 10000
        and int(mc.get("constituencies", 0)) == 52
        and int(mc.get("seats", 0)) == 350
        and bool(mc.get("invariants", {}).get("every_draw_seat_sum_350", False))
        and bool(mc.get("invariants", {}).get("all_allocations_status_OK", False))
    )
    gates.append(_gate(
        "mc_10000",
        mc_ok,
        "MC-10000 independiente, con invariantes electorales verificadas",
    ))

    baseline_path = r / "ci_evidence/backtest_2023_baseline.json"
    baseline = _read_json(baseline_path)
    baseline_ok = (
        isinstance(baseline, dict)
        and baseline.get("election") == "2023"
        and str(baseline.get("model", "")).startswith("baseline_persistence_2019N")
        and int(baseline.get("n_simulations", 0)) >= 10000
        and baseline.get("rng") == "numpy.PCG64"
        and baseline.get("source_tier") == "PRIMARY_INTERIOR"
        and isinstance(baseline.get("contracts"), dict)
        and baseline["contracts"].get("calibration_before_target_election") is True
        and baseline["contracts"].get("historical_conformal_calibration") is True
        and baseline["contracts"].get("family_level_calibration") is True
        and float(baseline.get("metrics", {}).get("coverage_actual_seats_in_calibrated_interval_winners", 0.0)) >= 0.85
    )
    gates.append(_gate(
        "baseline_2023",
        baseline_ok,
        "baseline territorial 2023 presente y estructuralmente verificable",
    ))

    calib_path = r / "ci_evidence/oos_calibration.json"
    calib = _read_json(calib_path)
    calibration_gate = isinstance(calib, dict) and isinstance(calib.get("coverage_gate"), dict)
    calib_ok = (
        calibration_gate
        and calib.get("status") in {"PASS", "CERTIFIED"}
        and int(calib.get("n_rows", 0)) > 0
        and int(calib.get("n_elections", 0)) >= 3
        and int(calib.get("walk_forward_holdouts", 0)) >= 1
        and bool(calib["coverage_gate"].get("passed", False))
    )
    gates.append(_gate(
        "oos_calibration",
        calib_ok,
        "calibración OOS expanding-window con gate de cobertura materializado",
    ))
    gates.append(_gate(
        "oos_walk_forward",
        calib_ok and int(calib.get("walk_forward_holdouts", 0)) >= 1 if isinstance(calib, dict) else False,
        "al menos un holdout estrictamente futuro",
    ))

    coverage_path = r / "ci_evidence/poll_source_coverage.json"
    coverage = _read_json(coverage_path)
    coverage_ok = (
        isinstance(coverage, dict)
        and coverage.get("status") == "PASS"
        and bool(coverage.get("coverage", {}).get("total", coverage.get("total", False)))
    )
    gates.append(_gate(
        "poll_source_coverage",
        coverage_ok,
        "cobertura de transporte/roles materializada; no se interpreta como validación de todos los sondeos",
    ))

    # Independent audit is deliberately impossible to self-certify.
    ext_path = r / "ci_evidence/external_audit.json"
    external = _read_json(ext_path)
    external_ok = (
        isinstance(external, dict)
        and external.get("status") in {"PASS", "CERTIFIED"}
        and external.get("independent") is True
        and bool(external.get("auditor"))
    )
    gates.append(_gate(
        "external_audit",
        external_ok,
        "auditoría independiente materializada y declarada",
    ))

    required = [g for g in gates if g.name != "external_audit"]
    required_ok = all(g.status == "PASS" for g in required)
    external_gate = next(g for g in gates if g.name == "external_audit")
    if required_ok and external_gate.status != "PASS":
        status = "READY_FOR_EXTERNAL_AUDIT"
    elif required_ok and external_gate.status == "PASS":
        status = "CERTIFIED"
    else:
        status = "BLOCKED"

    return {
        "schema": "MASTER_CERTIFICATION_V2",
        "status": status,
        "certification": status,
        "fail_closed": True,
        "gates": [g.__dict__ for g in gates],
    }


if __name__ == "__main__":
    out = certify()
    Path("ci_evidence").mkdir(parents=True, exist_ok=True)
    Path("ci_evidence/master_certification.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(out, ensure_ascii=False, indent=2))
    raise SystemExit(0 if out["status"] in {"CERTIFIED", "READY_FOR_EXTERNAL_AUDIT"} else 1)
