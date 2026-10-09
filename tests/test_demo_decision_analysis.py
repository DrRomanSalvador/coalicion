from __future__ import annotations
import json, subprocess, sys
from pathlib import Path
from scripts.demo_decision_analysis import build_analysis, viability_frontier

def test_analysis_is_auditable_and_reproducible():
    result, report = build_analysis()
    assert result["schema"] == "COALICION_DECISION_ANALYSIS_V1"
    assert result["official_certification"] == "NOT_INDEPENDENTLY_CERTIFIED"
    assert result["provenance"]["canonical_dataset_git_blob_sha1"]
    assert len(result["decision_log"]) == 4
    assert "Qué no puede concluirse" not in report
    assert "no presupone transferencias" in report

def test_decision_log_explains_deltas():
    result, _ = build_analysis()
    for entry in result["decision_log"]:
        assert entry["seat_delta"] == entry["coalition_seats"] - entry["separate_group_seats"]
        assert entry["causal_scope"] and entry["marginal_quotient_explanation"]
    madrid = next(x for x in result["decision_log"] if x["constituency"] == "Madrid" and x["scenario"] == "bloque_amplio_con_psoe_psc")
    assert madrid["seat_delta"] == 1

def test_frontier_holds_rival_votes_fixed():
    result = viability_frontier({"A": 400, "B": 350, "C": 250}, 3, 0, "B")
    assert result["additional_votes_minimum"] >= 0
    assert result["fixed_rival_votes"] is True
    assert result["valid_vote_total_increases_by"] == result["additional_votes_minimum"]

def test_cli_writes_json_and_report(tmp_path: Path):
    output, report = tmp_path/"analysis.json", tmp_path/"report.md"
    proc = subprocess.run([sys.executable, "scripts/demo_decision_analysis.py", "--output", str(output), "--report", str(report)],
                          capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert json.loads(output.read_text())["schema"] == "COALICION_DECISION_ANALYSIS_V1"
    assert "Informe ejecutivo" in report.read_text()
