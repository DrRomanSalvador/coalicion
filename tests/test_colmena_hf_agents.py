import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import colmena_queen_hf as queen
import colmena_agent_hf



def test_validate_missions_rejects_status_assigned_mismatch():
    missions = [
        {"id": f"M{i:04d}", "agent_id": f"agent-{i:03d}", "status": "PENDING", "assigned": False}
        for i in range(1, 180)
    ]
    missions[0].update({"status": "BLOCKED", "assigned": True})
    try:
        queen.validate_missions(missions)
    except ValueError as exc:
        assert "incoherentes" in str(exc)
    else:
        raise AssertionError("Debe rechazarse status/assigned incoherentes")


def test_mission_control_initializes_179_slots_without_claiming_execution(tmp_path, monkeypatch):
    path = tmp_path / "COLMENA_MISSION_CONTROL.json"
    monkeypatch.setattr(queen, "MISSION_CONTROL", path)
    missions = queen.get_missions()
    assert len(missions) == 179
    assert len({m["id"] for m in missions}) == 179
    assert all(m["status"] == "PENDING" and not m["task"] for m in missions)
    assert json.loads(path.read_text(encoding="utf-8"))["mode"] == "LOGICAL_SLOTS"


def test_assignment_refuses_undefined_tasks(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(queen, "MISSION_CONTROL", tmp_path / "missions.json")
    assert queen.assign_next_batch(5) == []
    assert "No hay misiones ejecutables" in capsys.readouterr().out


def test_assignment_is_bounded_and_only_assigns_concrete_tasks(tmp_path, monkeypatch):
    path = tmp_path / "missions.json"
    monkeypatch.setattr(queen, "MISSION_CONTROL", path)
    missions = queen.get_missions()
    for mission in missions[:8]:
        mission["task"] = "Audita el contrato de reproducibilidad indicado y cita evidencia."
    queen.save_json(path, {"schema": "COLMENA_MISSION_CONTROL_V1", "total": 179, "missions": missions})
    assert len(queen.assign_next_batch(5)) == 5
    assert len(queen.assign_next_batch(5)) == 3
    assert queen.assign_next_batch(5) == []


def test_agent_rejects_mission_without_task(tmp_path, monkeypatch):
    monkeypatch.setattr(colmena_agent_hf, "AGENTS_DIR", tmp_path)
    try:
        colmena_agent_hf.run_agent({"id": "M1", "agent_id": "agent-001"})
    except ValueError as exc:
        assert "task" in str(exc)
    else:
        raise AssertionError("La misión sin tarea debía rechazarse")



def test_result_reconciliation_records_review_without_allowing_model_pass(tmp_path, monkeypatch):
    path = tmp_path / "missions.json"
    monkeypatch.setattr(queen, "MISSION_CONTROL", path)
    monkeypatch.setattr(queen, "STATE_PATH", tmp_path / "state.json")
    missions = queen.get_missions()
    mission = missions[0]
    mission["task"] = "Revisar un contrato de prueba con evidencia."
    mission["status"] = "ASSIGNED"
    mission["assigned"] = True
    queen.save_json(path, {"schema": "COLMENA_MISSION_CONTROL_V1", "total": 179, "missions": missions})
    evidence = tmp_path / "evidence.json"
    evidence.write_text(json.dumps({
        "mission_id": mission["id"], "agent_id": mission["agent_id"],
        "status": "REVIEW_REQUIRED", "response": "Informe generado."
    }), encoding="utf-8")
    recorded = queen.record_result(evidence)
    assert recorded["status"] == "REVIEW_REQUIRED"
    assert queen.get_missions()[0]["status"] == "REVIEW_REQUIRED"
    assert recorded["evidence_sha256"]
    persisted_state = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert persisted_state["last_hf_agent_execution"]["mission_id"] == mission["id"]
    assert persisted_state["last_hf_agent_execution"]["evidence_sha256"] == recorded["evidence_sha256"]

    evidence.write_text(json.dumps({
        "mission_id": mission["id"], "agent_id": mission["agent_id"], "status": "PASS"
    }), encoding="utf-8")
    try:
        queen.record_result(evidence)
    except ValueError as exc:
        assert "PASS" in str(exc)
    else:
        raise AssertionError("La Reina no debe aceptar PASS certificado por un modelo")


def test_result_reconciliation_rejects_unassigned_or_wrong_agent(tmp_path, monkeypatch):
    path = tmp_path / "missions.json"
    monkeypatch.setattr(queen, "MISSION_CONTROL", path)
    missions = queen.get_missions()
    mission = missions[0]
    evidence = tmp_path / "evidence.json"
    evidence.write_text(json.dumps({
        "mission_id": mission["id"], "agent_id": mission["agent_id"],
        "status": "REVIEW_REQUIRED"
    }), encoding="utf-8")
    try:
        queen.record_result(evidence)
    except ValueError as exc:
        assert "no está asignada" in str(exc)
    else:
        raise AssertionError("Se rechazaba registrar una misión no asignada")



def test_reassign_blocked_mission_preserves_previous_evidence_and_reopens(tmp_path, monkeypatch):
    path = tmp_path / "missions.json"
    monkeypatch.setattr(queen, "MISSION_CONTROL", path)
    missions = queen.get_missions()
    mission = missions[0]
    mission.update({
        "task": "Reintento controlado.",
        "status": "BLOCKED",
        "assigned": False,
        "assigned_at": "2026-10-09T12:00:00+00:00",
        "result_recorded_at": "2026-10-09T12:01:00+00:00",
        "evidence_path": "artifacts/old.json",
        "evidence_sha256": "abc123",
        "result_summary": "Proveedor no disponible",
    })
    queen.save_json(path, {"schema": "COLMENA_MISSION_CONTROL_V1", "total": 179, "missions": missions})
    result = queen.reassign_blocked("M0001")
    reopened = queen.get_missions()[0]
    assert result["status"] == "ASSIGNED"
    assert reopened["status"] == "ASSIGNED" and reopened["assigned"] is True
    assert reopened["attempt_history"][-1]["evidence_sha256"] == "abc123"
    assert reopened["attempt_history"][-1]["status"] == "BLOCKED"



def test_reassign_blocked_clears_current_evidence_fields_after_archiving_metadata(tmp_path, monkeypatch):
    path = tmp_path / "missions.json"
    monkeypatch.setattr(queen, "MISSION_CONTROL", path)
    missions = queen.get_missions()
    missions[0].update({
        "task": "Tarea de reintento",
        "status": "BLOCKED",
        "assigned": False,
        "result_recorded_at": "old-time",
        "evidence_path": "old.json",
        "evidence_sha256": "old-hash",
        "result_summary": "old failure",
    })
    queen.save_json(path, {"schema": "COLMENA_MISSION_CONTROL_V1", "total": 179, "missions": missions})
    queen.reassign_blocked("M0001")
    reopened = queen.get_missions()[0]
    assert reopened["status"] == "ASSIGNED"
    assert "evidence_path" not in reopened
    assert "evidence_sha256" not in reopened
    assert "result_recorded_at" not in reopened
    assert reopened["attempt_history"][-1]["evidence_sha256"] == "old-hash"


def test_reassign_blocked_refuses_non_blocked_or_taskless_mission(tmp_path, monkeypatch):
    path = tmp_path / "missions.json"
    monkeypatch.setattr(queen, "MISSION_CONTROL", path)
    missions = queen.get_missions()
    missions[0].update({"task": "Tarea concreta", "status": "ASSIGNED", "assigned": True})
    queen.save_json(path, {"schema": "COLMENA_MISSION_CONTROL_V1", "total": 179, "missions": missions})
    try:
        queen.reassign_blocked("M0001")
    except ValueError as exc:
        assert "BLOCKED" in str(exc)
    else:
        raise AssertionError("No debe reabrirse una misión que no esté BLOCKED")

    missions = queen.get_missions()
    missions[0].update({"task": "", "status": "BLOCKED", "assigned": False})
    queen.save_json(path, {"schema": "COLMENA_MISSION_CONTROL_V1", "total": 179, "missions": missions})
    try:
        queen.reassign_blocked("M0001")
    except ValueError as exc:
        assert "sin tarea concreta" in str(exc)
    else:
        raise AssertionError("No debe reabrirse una misión sin tarea")


def test_agent_uses_exact_reina_token_name(tmp_path, monkeypatch):
    monkeypatch.setattr(colmena_agent_hf, "AGENTS_DIR", tmp_path / "evidence")
    monkeypatch.setattr(colmena_agent_hf, "MISSION_CONTROL", tmp_path / "missions.json")
    mission = {
        "id": "M0001", "agent_id": "agent-001",
        "task": "Prueba controlada.", "status": "ASSIGNED", "assigned": True
    }
    (tmp_path / "missions.json").write_text(json.dumps({
        "schema": "COLMENA_MISSION_CONTROL_V1", "total": 179,
        "missions": [mission] + [
            {"id": f"M{i:04d}", "agent_id": f"agent-{i:03d}",
             "task": "", "status": "PENDING", "assigned": False}
            for i in range(2, 180)
        ]
    }), encoding="utf-8")
    monkeypatch.delenv("Reina_token", raising=False)
    monkeypatch.setenv("HF_TOKEN", "must-not-be-used")
    result = colmena_agent_hf.run_agent({
        "id": "M0001", "agent_id": "agent-001", "task": "Prueba controlada."
    })
    assert result["status"] == "BLOCKED"
    assert "Reina_token" in result["error"]
    assert (tmp_path / "evidence" / "agent-001_M0001.json").is_file()



def test_auto_provider_falls_back_only_for_unsupported_provider(tmp_path, monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(colmena_agent_hf, "AGENTS_DIR", tmp_path / "evidence")
    control_path = tmp_path / "missions.json"
    monkeypatch.setattr(colmena_agent_hf, "MISSION_CONTROL", control_path)
    mission = {"id": "M0001", "agent_id": "agent-001", "task": "Fallback",
               "status": "ASSIGNED", "assigned": True, "context_paths": []}
    control_path.write_text(json.dumps({"schema": "COLMENA_MISSION_CONTROL_V1",
                                        "total": 179, "missions": [mission]}), encoding="utf-8")
    attempted = []
    class FakeClient:
        def __init__(self, **kwargs):
            self.provider = kwargs["provider"]
            attempted.append(self.provider)
        def chat_completion(self, **kwargs):
            if self.provider == "deepinfra":
                raise RuntimeError("model_not_supported")
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="Informe."))])
    monkeypatch.setitem(sys.modules, "huggingface_hub", SimpleNamespace(InferenceClient=FakeClient))
    monkeypatch.setenv("HF_PROVIDER_FALLBACKS", "deepinfra,featherless-ai")
    result = colmena_agent_hf.run_agent(mission, hf_token="test-token", model="example/model", provider="auto")
    assert attempted == ["deepinfra", "featherless-ai"]
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["provider"] == "featherless-ai"


def test_auto_provider_fallback_does_not_retry_auth_or_rate_limit_errors(tmp_path, monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(colmena_agent_hf, "AGENTS_DIR", tmp_path / "evidence")
    control_path = tmp_path / "missions.json"
    monkeypatch.setattr(colmena_agent_hf, "MISSION_CONTROL", control_path)
    mission = {"id": "M0001", "agent_id": "agent-001", "task": "No unsafe retries",
               "status": "ASSIGNED", "assigned": True, "context_paths": []}
    control_path.write_text(json.dumps({"schema": "COLMENA_MISSION_CONTROL_V1",
                                        "total": 179, "missions": [mission]}), encoding="utf-8")
    attempted = []
    class FakeClient:
        def __init__(self, **kwargs):
            attempted.append(kwargs["provider"])
        def chat_completion(self, **kwargs):
            raise RuntimeError("401 Unauthorized")
    monkeypatch.setitem(sys.modules, "huggingface_hub", SimpleNamespace(InferenceClient=FakeClient))
    monkeypatch.setenv("HF_PROVIDER_FALLBACKS", "deepinfra,featherless-ai")
    result = colmena_agent_hf.run_agent(mission, hf_token="test-token", model="example/model", provider="auto")
    assert attempted == ["deepinfra"]
    assert result["status"] == "BLOCKED"
    assert "401 Unauthorized" in result["error"]


def test_agent_refuses_unassigned_mission_before_provider_call(tmp_path, monkeypatch):
    monkeypatch.setattr(colmena_agent_hf, "AGENTS_DIR", tmp_path / "evidence")
    monkeypatch.setattr(colmena_agent_hf, "MISSION_CONTROL", tmp_path / "missions.json")
    missions = [
        {"id": f"M{i:04d}", "agent_id": f"agent-{i:03d}", "task": "",
         "status": "PENDING", "assigned": False}
        for i in range(1, 180)
    ]
    missions[0]["task"] = "No ejecutar si no está asignada."
    (tmp_path / "missions.json").write_text(json.dumps({
        "schema": "COLMENA_MISSION_CONTROL_V1", "total": 179, "missions": missions
    }), encoding="utf-8")
    monkeypatch.setenv("Reina_token", "test-token")
    try:
        colmena_agent_hf.run_agent({
            "id": "M0001", "agent_id": "agent-001", "task": "No ejecutar si no está asignada."
        })
    except ValueError as exc:
        assert "no ha asignado" in str(exc)
    else:
        raise AssertionError("El agente no debe ejecutar misiones pendientes")


def test_agent_context_paths_are_bounded_and_repo_relative(tmp_path, monkeypatch):
    monkeypatch.setattr(colmena_agent_hf, "ROOT", tmp_path)
    allowed = tmp_path / "safe.py"
    allowed.write_text("def safe(): return True\n", encoding="utf-8")
    assert "def safe" in colmena_agent_hf.load_context({"context_paths": ["safe.py"]})
    try:
        colmena_agent_hf.load_context({"context_paths": ["../outside.py"]})
    except ValueError as exc:
        assert "no permitida" in str(exc)
    else:
        raise AssertionError("Debe bloquear rutas fuera del repositorio")


def test_canonical_mission_control_has_next_five_executable_tasks():
    control = json.loads((ROOT / "docs" / "COLMENA_MISSION_CONTROL.json").read_text(encoding="utf-8"))
    missions = control["missions"]
    assert len(missions) == 179
    assert len({m["id"] for m in missions}) == 179
    next_five = [m for m in missions if m["id"] in {f"M{i:04d}" for i in range(6, 11)}]
    assert len(next_five) == 5
    assert all(m["status"] in {"PENDING", "ASSIGNED"} for m in next_five)
    assert all(m["assigned"] is (m["status"] == "ASSIGNED") for m in next_five)
    assert all(isinstance(m["task"], str) and m["task"].strip() for m in next_five)
    assert all(isinstance(m.get("context_paths"), list) and m["context_paths"] for m in next_five)


def test_agent_routes_provider_and_explains_model_not_supported(tmp_path, monkeypatch):
    from types import SimpleNamespace
    import pytest

    monkeypatch.setattr(colmena_agent_hf, "AGENTS_DIR", tmp_path / "evidence")
    control_path = tmp_path / "missions.json"
    monkeypatch.setattr(colmena_agent_hf, "MISSION_CONTROL", control_path)
    mission = {
        "id": "M0001", "agent_id": "agent-001", "task": "Prueba de proveedor.",
        "status": "ASSIGNED", "assigned": True, "context_paths": []
    }
    control_path.write_text(json.dumps({
        "schema": "COLMENA_MISSION_CONTROL_V1", "total": 179, "missions": [mission]
    }), encoding="utf-8")
    captured = {}

    class FakeClient:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def chat_completion(self, **kwargs):
            raise RuntimeError("model_not_supported: not supported by any provider")

    monkeypatch.setitem(sys.modules, "huggingface_hub", SimpleNamespace(InferenceClient=FakeClient))
    result = colmena_agent_hf.run_agent(
        mission, hf_token="test-token", model="example/model", provider="deepinfra"
    )
    assert captured["provider"] == "deepinfra"
    assert result["status"] == "BLOCKED"
    assert "Ninguno acepta este modelo" in result["error"]
    assert "HF_PROVIDER_FALLBACKS" in result["error"]
