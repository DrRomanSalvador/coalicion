from __future__ import annotations
import json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CONTROL=ROOT/"docs/COLMENA_MISSION_CONTROL.json"

def test_queen_plan_covers_every_mission(tmp_path):
    out=tmp_path/"approval.json"
    p=subprocess.run([sys.executable,"scripts/colmena_queen.py","--ref","test-ref","--output",str(out)],cwd=ROOT,text=True,capture_output=True)
    assert p.returncode==0, p.stderr
    d=json.loads(out.read_text())
    registry=json.loads(CONTROL.read_text())
    assert len(d["missions"])==len(registry["missions"])
    assert len({m["id"] for m in d["missions"]})==len(d["missions"])
    assert all(m["write_authorized"] is False for m in d["missions"])

def test_worker_rejects_tampered_approval(tmp_path):
    out=tmp_path/"approval.json"
    subprocess.run([sys.executable,"scripts/colmena_queen.py","--ref","test-ref","--output",str(out)],cwd=ROOT,check=True)
    d=json.loads(out.read_text())
    d["missions"][0]["approval"]="tampered"
    out.write_text(json.dumps(d),encoding="utf-8")
    ev=tmp_path/"evidence.json"
    p=subprocess.run([sys.executable,"scripts/colmena_worker.py","--mission-id",d["missions"][0]["id"],"--approval",str(out),"--ref","test-ref","--out",str(ev)],cwd=ROOT,text=True,capture_output=True)
    assert p.returncode!=0

def test_workflow_binds_reina_secret_without_printing_it():
    workflow=(ROOT/".github/workflows/colmena_atomic_swarm.yml").read_text(encoding="utf-8")
    assert "HF_TOKEN: ${{ secrets.reina_TOKEN }}" in workflow
    assert "if [[ -z \"${HF_TOKEN:-}\" ]]" in workflow
    assert "echo \"${HF_TOKEN}" not in workflow
    assert "print(\"${HF_TOKEN}" not in workflow
    assert "Persist operational state (fail-closed)" in workflow
    assert "timestamp_europe_madrid" in workflow


def test_regression_missions_use_bounded_targeted_pytest_commands():
    from scripts.colmena_worker import command_for

    cases = {
        "regresión motor electoral": "tests/test_electoral.py",
        "regresión coaliciones": "tests/test_coalition.py",
        "regresión incertidumbre": "tests/test_uncertainty.py",
        "regresión bot": "tests/test_telegram_bot.py",
        "regresión monitor": "tests/test_poll_monitor.py",
        "regresión Telegram": "tests/test_telegram_integration.py",
    }
    for mission, expected_path in cases.items():
        command, adapter = command_for(mission)
        assert adapter == "TARGETED_PYTEST"
        assert expected_path in command
        assert command != [sys.executable, "-m", "pytest", "-q"]


def test_exhaustive_test_mission_keeps_full_pytest_suite():
    from scripts.colmena_worker import command_for

    command, adapter = command_for("batería completa de tests")
    assert adapter == "FULL_PYTEST"
    assert command == [sys.executable, "-m", "pytest", "-q"]


def test_queen_swarm_timeout_allows_bounded_execution_window():
    workflow = (ROOT / ".github/workflows/colmena_atomic_swarm.yml").read_text(encoding="utf-8")
    assert 'timeout-minutes: 350' in workflow


def test_swarm_operational_state_json_uses_real_newline_not_literal_backslash_n():
    workflow = (ROOT / ".github/workflows/colmena_atomic_swarm.yml").read_text(encoding="utf-8")
    line = next(line for line in workflow.splitlines() if 'operational_state.json' in line)
    assert r'"\\n"' not in line
    assert r'"\n"' in line


def test_seec_convergence_diagnostics_include_latent_eta_states():
    script = (ROOT / "scripts/run_seec_production.py").read_text(encoding="utf-8")
    assert 'diagnostic_variables=["temporal_sigma","log_concentration","eta0","eta"]' in script
    assert '"latent_eta_included":True' in script


def test_unmapped_mission_analysis_cannot_be_reported_as_pass():
    from scripts.colmena_worker import run

    mission = {
        "id": "M0004-52-circunscripciones",
        "title": "unmapped conceptual mission with no validator",
        "kind": "READ",
        "write_authorized": False,
        "scope": [],
        "approval": "test-approval",
    }
    evidence = run(
        mission,
        "test-ref",
        "agent-M0004",
        {"provider": "test", "execution_id": "test-exec", "independent": True, "ai_execution": True},
    )
    assert evidence["status"] == "BLOCKED"
    assert evidence["returncode"] == 2
    assert "deterministic validator" in evidence["stderr"]


def test_unapproved_change_mission_cannot_be_reported_as_pass():
    from scripts.colmena_worker import run

    mission = {
        "id": "M0179-release-v1-0-0",
        "title": "release v1.0.0",
        "kind": "WRITE",
        "write_authorized": False,
        "scope": [],
        "approval": "test-approval",
    }
    evidence = run(
        mission,
        "test-ref",
        "agent-M0179",
        {"provider": "test", "execution_id": "test-exec", "independent": True, "ai_execution": True},
    )
    assert evidence["status"] == "BLOCKED"
    assert evidence["returncode"] == 2
    assert "scoped write approval" in evidence["stderr"]


def test_read_only_missions_resolve_to_real_validators():
    from scripts.colmena_worker import command_for

    cases = {
        "52 circunscripciones": "tests/test_electoral.py",
        "manifest procedencia": "tests/test_official_interior_workbook.py",
        "invariantes matemáticos": "tests/test_architecture_invariants.py",
        "invariantes coalición": "tests/test_coalition.py",
        "propagación incertidumbre": "tests/test_uncertainty.py",
        "prohibir inferencia nacional-territorial": "tests/test_territorial_prediction_2026.py",
    }
    for mission, expected in cases.items():
        command, adapter = command_for(mission)
        assert adapter == "MISSION_VALIDATOR"
        assert expected in command


def test_update_missions_are_write_gated_in_queen_and_worker():
    from scripts.colmena_queen import classify
    from scripts.colmena_worker import command_for, run

    title = "actualizar un artefacto no verificado"
    assert classify(title) == "WRITE"
    command, adapter = command_for(title)
    assert command is None
    assert adapter == "WRITE_OR_CHANGE_REQUIRES_EXPLICIT_SCOPE"
    evidence = run(
        {"id": "M0024", "title": title, "kind": "WRITE", "write_authorized": False, "scope": [], "approval": "test"},
        "test-ref",
        "agent-M0024",
        {"provider": "test", "execution_id": "test-exec", "independent": True, "ai_execution": True},
    )
    assert evidence["status"] == "BLOCKED"


def test_edge_case_and_operational_missions_map_to_specific_validators():
    from scripts.colmena_worker import command_for

    cases = {
        "normalización determinista etiquetas": "tests/test_fallback_normalization.py",
        "prohibir datos sintéticos silenciosos": "tests/test_adversarial_audit.py",
        "test valores negativos": "tests/test_adversarial_audit.py",
        "test fechas inválidas": "tests/test_hardening.py",
        "decisión.py": "tests/test_decision.py",
        "detección elecciones": "tests/test_official_interior_workbook.py",
        "SEEC jerárquico": "tests/test_seec_production.py",
        "convergencia real": "tests/test_seec_production.py",
        "CI de artefactos": "tests/test_evidence_certificate.py",
        "ausencia de segundo D’Hondt": "tests/test_architecture_invariants.py",
    }
    for mission, expected_path in cases.items():
        command, adapter = command_for(mission)
        assert adapter == "MISSION_VALIDATOR", (mission, adapter)
        assert expected_path in command, (mission, command)


def test_already_materialized_mutation_missions_use_read_only_state_validators():
    from scripts.colmena_worker import command_for

    cases = {
        "integración física Elecciones-Congreso.xlsx": "tests/test_official_interior_workbook.py",
        "conexión data.py dominio": "tests/test_canonical_architecture.py",
        "eliminación transformaciones incompatibles": "tests/test_architecture_invariants.py",
        "actualizar telegram_product_checkpoint": "tests/test_product_layer.py",
        "actualizar estado/certificación": "tests/test_master_certification.py",
    }
    for mission, expected_path in cases.items():
        command, adapter = command_for(mission)
        assert adapter == "MISSION_STATE_VALIDATOR", (mission, adapter)
        assert expected_path in command, (mission, command)

    release_command, release_adapter = command_for("release v1.0.0")
    assert release_command is None
    assert release_adapter == "WRITE_OR_CHANGE_REQUIRES_EXPLICIT_SCOPE"
