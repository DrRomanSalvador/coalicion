import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import colmena_queen as queen
import colmena_agent_ollama as colmena_agent_ollama



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
    monkeypatch.setattr(queen, "STATE_PATH", tmp_path / "state.json")
    assert queen.assign_next_batch(5) == []
    assert "No hay misiones ejecutables" in capsys.readouterr().out


def test_assignment_is_bounded_and_only_assigns_concrete_tasks(tmp_path, monkeypatch):
    path = tmp_path / "missions.json"
    monkeypatch.setattr(queen, "MISSION_CONTROL", path)
    monkeypatch.setattr(queen, "STATE_PATH", tmp_path / "state.json")
    missions = queen.get_missions()
    for mission in missions[:8]:
        mission["task"] = "Audita el contrato de reproducibilidad indicado y cita evidencia."
    queen.save_json(path, {"schema": "COLMENA_MISSION_CONTROL_V1", "total": 179, "missions": missions})
    assert len(queen.assign_next_batch(5)) == 5
    assert len(queen.assign_next_batch(5)) == 3
    assert queen.assign_next_batch(5) == []
    summary = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))["queen_coordination"]
    assert summary["assigned"] == 8
    assert summary["pending"] == 171
    assert summary["tasks_defined"] == 8
    assert summary["status"] == "MISSIONS_ASSIGNED"
    assert summary["source_of_truth"] == "docs/COLMENA_MISSION_CONTROL.json"


def test_agent_rejects_mission_without_task(tmp_path, monkeypatch):
    monkeypatch.setattr(colmena_agent_ollama, "AGENTS_DIR", tmp_path)
    try:
        colmena_agent_ollama.run_agent({"id": "M1", "agent_id": "agent-001"})
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
    assert persisted_state["last_agent_execution"]["mission_id"] == mission["id"]
    assert persisted_state["last_agent_execution"]["evidence_sha256"] == recorded["evidence_sha256"]
    assert persisted_state["queen_coordination"]["review_required"] == 1
    assert persisted_state["queen_coordination"]["pending"] == 178
    assert persisted_state["queen_coordination"]["assigned"] == 0
    assert persisted_state["queen_coordination"]["status"] == "REVIEW_REQUIRED"

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
    monkeypatch.setattr(queen, "STATE_PATH", tmp_path / "state.json")
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
    monkeypatch.setattr(queen, "STATE_PATH", tmp_path / "state.json")
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
    monkeypatch.setattr(queen, "STATE_PATH", tmp_path / "state.json")
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


def test_ollama_backend_runs_without_external_credits(tmp_path, monkeypatch):
    import urllib.request
    from io import BytesIO

    mission_path = tmp_path / "missions.json"
    monkeypatch.setattr(colmena_agent_ollama, "MISSION_CONTROL", mission_path)
    monkeypatch.setattr(colmena_agent_ollama, "AGENTS_DIR", tmp_path / "evidence")
    mission = {
        "id": "M0001", "agent_id": "agent-001", "task": "Audita el código",
        "status": "ASSIGNED", "assigned": True, "context_paths": []
    }
    mission_path.write_text(json.dumps({"schema": "COLMENA_MISSION_CONTROL_V1", "total": 179,
                                       "missions": [mission]}), encoding="utf-8")
    class FakeResponse:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self):
            return json.dumps({"message": {"content": "Hallazgo verificable."}}).encode("utf-8")
    calls = []
    def fake_urlopen(request, timeout):
        calls.append((request.full_url, timeout, json.loads(request.data.decode("utf-8"))))
        return FakeResponse()
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    monkeypatch.delenv("Reina_token", raising=False)

    result = colmena_agent_ollama.run_agent(
        mission, hf_token=None, backend="ollama", local_model="qwen2.5:3b",
        ollama_url="http://127.0.0.1:11434"
    )

    assert result["status"] == "REVIEW_REQUIRED"
    assert result["backend"] == "ollama"
    assert result["provider"] == "local-ollama"
    assert result["response"] == "Hallazgo verificable."
    assert len(calls) == 1
    assert calls[0][0] == "http://127.0.0.1:11434/api/chat"
    assert calls[0][2]["model"] == "qwen2.5:3b"
    assert (tmp_path / "evidence" / "agent-001_M0001.json").is_file()


def test_ollama_backend_failure_stays_blocked(tmp_path, monkeypatch):
    import urllib.request
    from urllib.error import URLError

    mission_path = tmp_path / "missions.json"
    monkeypatch.setattr(colmena_agent_ollama, "MISSION_CONTROL", mission_path)
    monkeypatch.setattr(colmena_agent_ollama, "AGENTS_DIR", tmp_path / "evidence")
    mission = {
        "id": "M0001", "agent_id": "agent-001", "task": "Audita el código",
        "status": "ASSIGNED", "assigned": True, "context_paths": []
    }
    mission_path.write_text(json.dumps({"schema": "COLMENA_MISSION_CONTROL_V1", "total": 179,
                                       "missions": [mission]}), encoding="utf-8")
    def fail_urlopen(request, timeout):
        raise URLError("Ollama no está iniciado")
    monkeypatch.setattr(urllib.request, "urlopen", fail_urlopen)
    monkeypatch.delenv("Reina_token", raising=False)

    result = colmena_agent_ollama.run_agent(mission, backend="ollama")

    assert result["status"] == "BLOCKED"
    assert result["backend"] == "ollama"
    assert "Ollama" in result["error"]
    assert "Ollama" in result["error"]


def test_ollama_agent_fails_closed_for_unassigned_mission(tmp_path, monkeypatch):
    monkeypatch.setattr(colmena_agent_ollama, "MISSION_CONTROL", tmp_path / "missions.json")
    monkeypatch.setattr(colmena_agent_ollama, "AGENTS_DIR", tmp_path / "evidence")
    (tmp_path / "missions.json").write_text(json.dumps({
        "missions": [{"id": "M0001", "agent_id": "agent-001", "task": "Auditar", "status": "PENDING", "assigned": False}]
    }), encoding="utf-8")
    result = colmena_agent_ollama.run_agent("M0001")
    assert result["status"] == "BLOCKED"
    assert "Reina no ha asignado" in result["error"]
    assert (tmp_path / "evidence" / "agent-001_M0001.json").is_file()


def test_ollama_agent_does_not_accept_external_provider_configuration(monkeypatch):
    monkeypatch.delenv("Reina_token", raising=False)
    monkeypatch.delenv("HF_TOKEN", raising=False)
    assert "huggingface_hub" not in sys.modules
