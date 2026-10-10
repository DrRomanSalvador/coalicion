import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import colmena_queen as queen
import colmena_agent_ollama as agent


def test_mission_ledger_rejects_status_assigned_mismatch():
    missions = [
        {"id": f"M{i:04d}", "agent_id": f"agent-{i:03d}", "status": "PENDING", "assigned": False}
        for i in range(1, 180)
    ]
    missions[0].update(status="BLOCKED", assigned=True)
    try:
        queen.validate_missions(missions)
    except ValueError as exc:
        assert "incoherentes" in str(exc)
    else:
        raise AssertionError("El ledger debe rechazar status/assigned incoherentes")


def test_assignment_is_bounded_and_requires_concrete_tasks(tmp_path, monkeypatch):
    ledger, state = tmp_path / "missions.json", tmp_path / "state.json"
    monkeypatch.setattr(queen, "MISSION_CONTROL", ledger)
    monkeypatch.setattr(queen, "STATE_PATH", state)
    missions = queen.get_missions()
    for mission in missions[:7]:
        mission["task"] = "Auditar un contrato concreto con evidencia."
    queen.save_json(ledger, {"schema": "COLMENA_MISSION_CONTROL_V1", "total": 179, "missions": missions})
    assert len(queen.assign_next_batch(5)) == 5
    assert len(queen.assign_next_batch(5)) == 2
    assert queen.assign_next_batch(5) == []
    saved = json.loads(ledger.read_text(encoding="utf-8"))
    assert sum(m["status"] == "ASSIGNED" for m in saved["missions"]) == 7


def test_agent_fails_closed_without_assignment(tmp_path, monkeypatch):
    ledger = tmp_path / "missions.json"
    monkeypatch.setattr(agent, "MISSION_CONTROL", ledger)
    monkeypatch.setattr(agent, "AGENTS_DIR", tmp_path / "evidence")
    ledger.write_text(json.dumps({"missions": [{
        "id": "M0001", "agent_id": "agent-001", "task": "Auditar", "status": "PENDING", "assigned": False
    }]}), encoding="utf-8")
    result = agent.run_agent("M0001")
    assert result["status"] == "BLOCKED"
    assert "Reina no ha asignado" in result["error"]
    assert (tmp_path / "evidence" / "agent-001_M0001.json").is_file()


def test_agent_uses_ollama_without_external_token(tmp_path, monkeypatch):
    ledger = tmp_path / "missions.json"
    monkeypatch.setattr(agent, "MISSION_CONTROL", ledger)
    monkeypatch.setattr(agent, "AGENTS_DIR", tmp_path / "evidence")
    monkeypatch.setattr(agent, "ROOT", tmp_path)
    monkeypatch.setattr(agent, "load_mandatory_contract", lambda: "CONTRATO DE PRUEBA; principios 01–25.")
    ledger.write_text(json.dumps({"missions": [{
        "id": "M0001", "agent_id": "agent-001", "task": "Audita el código",
        "status": "ASSIGNED", "assigned": True, "context_paths": []
    }]}), encoding="utf-8")
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self): return json.dumps({"message": {"content": "Hallazgo verificable."}}).encode()
    calls = []
    def fake_urlopen(request, timeout):
        calls.append((request.full_url, timeout, json.loads(request.data.decode())))
        return Response()
    monkeypatch.setattr(agent, "urlopen", fake_urlopen)
    monkeypatch.delenv("Reina_token", raising=False)
    monkeypatch.delenv("HF_TOKEN", raising=False)
    result = agent.run_agent("M0001", model="qwen2.5:3b", ollama_url="http://127.0.0.1:11434")
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["provider"] == "local-ollama"
    assert result["response"] == "Hallazgo verificable."
    assert calls[0][0] == "http://127.0.0.1:11434/api/chat"
    assert calls[0][2]["model"] == "qwen2.5:3b"
    system_prompt = calls[0][2]["messages"][0]["content"]
    assert "regla boy scout" in system_prompt
    assert "CONTRATO DE PRUEBA; principios 01–25." in system_prompt


def test_ollama_failure_is_blocked_and_never_falls_back(tmp_path, monkeypatch):
    from urllib.error import URLError
    ledger = tmp_path / "missions.json"
    monkeypatch.setattr(agent, "MISSION_CONTROL", ledger)
    monkeypatch.setattr(agent, "AGENTS_DIR", tmp_path / "evidence")
    monkeypatch.setattr(agent, "load_mandatory_contract", lambda: "CONTRATO DE PRUEBA; principios 01–25.")
    ledger.write_text(json.dumps({"missions": [{
        "id": "M0001", "agent_id": "agent-001", "task": "Audita",
        "status": "ASSIGNED", "assigned": True, "context_paths": []
    }]}), encoding="utf-8")
    def fail_urlopen(request, timeout): raise URLError("Ollama no está iniciado")
    monkeypatch.setattr(agent, "urlopen", fail_urlopen)
    result = agent.run_agent("M0001")
    assert result["status"] == "BLOCKED"
    assert result["provider"] == "local-ollama"
    assert "huggingface" not in json.dumps(result).lower()
    assert (tmp_path / "evidence" / "agent-001_M0001.json").is_file()


def test_model_result_cannot_mark_mission_pass(tmp_path, monkeypatch):
    ledger, state = tmp_path / "missions.json", tmp_path / "state.json"
    monkeypatch.setattr(queen, "MISSION_CONTROL", ledger)
    monkeypatch.setattr(queen, "STATE_PATH", state)
    missions = queen.get_missions()
    missions[0].update(task="Revisar contrato.", status="ASSIGNED", assigned=True)
    queen.save_json(ledger, {"schema": "COLMENA_MISSION_CONTROL_V1", "total": 179, "missions": missions})
    evidence = tmp_path / "evidence.json"
    evidence.write_text(json.dumps({"mission_id": "M0001", "agent_id": "agent-001", "status": "PASS"}), encoding="utf-8")
    try:
        queen.record_result(evidence)
    except ValueError as exc:
        assert "PASS" in str(exc)
    else:
        raise AssertionError("La Reina no debe aceptar PASS de un modelo")


def test_ollama_workflow_uses_one_model_store_for_server_and_pull():
    source = (ROOT / ".github/workflows/colmena_ollama_agents.yml").read_text(encoding="utf-8")
    assert 'export OLLAMA_MODELS="$HOME/.ollama/models"' in source
    assert "(ollama serve > /tmp/ollama-pull.log 2>&1 &)" in source
    assert "(ollama serve > /tmp/ollama-execute.log 2>&1 &)" in source
    assert 'ollama pull "$LOCAL_MODEL"' in source
    assert 'ollama list | grep -F "$LOCAL_MODEL"' in source
    execution_step = source.split("- name: Validar misión asignada y ejecutar solo Ollama", 1)[1].split("- name: Reconciliar resultado", 1)[0]
    assert 'export OLLAMA_MODELS="$HOME/.ollama/models"' in execution_step
    assert "Ollama no está disponible en el paso de ejecución." in execution_step


def test_lightweight_workflow_never_pushes_directly_to_main():
    source = (ROOT / ".github/workflows/colmena_atomic_swarm.yml").read_text(encoding="utf-8")
    assert "git push origin HEAD:main" not in source
    assert "contents: read" in source
    assert "actions/upload-artifact@v4" in source
    assert '"main_modified": False' in source
    assert "colmena-light-checkpoint-" in source


def test_assignment_workflow_treats_no_executable_tasks_as_safe_noop():
    source = (ROOT / ".github/workflows/colmena_ollama_assign.yml").read_text(encoding="utf-8")
    assert "python scripts/colmena_queen.py --assign" in source
    assert "peter-evans/create-pull-request@v7" in source



def test_ollama_context_paths_are_repo_relative_and_bounded(tmp_path, monkeypatch):
    monkeypatch.setattr(agent, "ROOT", tmp_path)
    allowed = tmp_path / "safe.py"
    allowed.write_text("def safe(): return True\n", encoding="utf-8")
    assert "def safe" in agent.load_context({"context_paths": ["safe.py"]})
    try:
        agent.load_context({"context_paths": ["../outside.py"]})
    except ValueError as exc:
        assert "no permitida" in str(exc)
    else:
        raise AssertionError("Debe bloquear rutas fuera del repositorio")
    try:
        agent.load_context({"context_paths": ["safe.py"] * 5})
    except ValueError as exc:
        assert "hasta 4" in str(exc)
    else:
        raise AssertionError("Debe limitar los archivos de contexto")
    oversized = tmp_path / "oversized.txt"
    oversized.write_text("x" * 12001, encoding="utf-8")
    try:
        agent.load_context({"context_paths": ["oversized.txt"]})
    except ValueError as exc:
        assert "12000" in str(exc)
    else:
        raise AssertionError("Debe rechazar archivos de contexto excesivos")


def test_reassign_blocked_archives_evidence_and_clears_stale_fields(tmp_path, monkeypatch):
    ledger, state = tmp_path / "missions.json", tmp_path / "state.json"
    monkeypatch.setattr(queen, "MISSION_CONTROL", ledger)
    monkeypatch.setattr(queen, "STATE_PATH", state)
    missions = queen.get_missions()
    missions[0].update({
        "task": "Reintento controlado.", "status": "BLOCKED", "assigned": False,
        "evidence_path": "artifacts/old.json", "evidence_sha256": "abc123",
        "result_recorded_at": "old-time", "result_summary": "Ollama no disponible",
    })
    queen.save_json(ledger, {"schema": "COLMENA_MISSION_CONTROL_V1", "total": 179, "missions": missions})
    queen.reassign_blocked("M0001")
    reopened = queen.get_missions()[0]
    assert reopened["status"] == "ASSIGNED" and reopened["assigned"] is True
    assert reopened["attempt_history"][-1]["status"] == "BLOCKED"
    assert reopened["attempt_history"][-1]["evidence_sha256"] == "abc123"
    for key in ("evidence_path", "evidence_sha256", "result_recorded_at", "result_summary"):
        assert key not in reopened


def test_canonical_next_five_missions_have_concrete_tasks_and_context():
    control = json.loads((ROOT / "docs/COLMENA_MISSION_CONTROL.json").read_text(encoding="utf-8"))
    missions = control["missions"]
    assert len(missions) == 179
    assert len({m["id"] for m in missions}) == 179
    selected = [m for m in missions if m["id"] in {f"M{i:04d}" for i in range(6, 11)}]
    assert len(selected) == 5
    assert all(m["status"] in {"PENDING", "ASSIGNED"} for m in selected)
    assert all(m["assigned"] is (m["status"] == "ASSIGNED") for m in selected)
    assert all(isinstance(m.get("task"), str) and m["task"].strip() for m in selected)
    assert all(isinstance(m.get("context_paths"), list) and m["context_paths"] for m in selected)


def test_ollama_agent_has_no_remote_inference_client():
    source = (ROOT / "scripts/colmena_agent_ollama.py").read_text(encoding="utf-8").lower()
    assert "huggingface_hub" not in source
    assert "inferenceclient" not in source
    assert "hf_token" not in source
    assert "/api/chat" in source



def test_assignment_refuses_undefined_tasks(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(queen, "MISSION_CONTROL", tmp_path / "missions.json")
    monkeypatch.setattr(queen, "STATE_PATH", tmp_path / "state.json")
    assert queen.assign_next_batch(5) == []
    assert "No hay misiones ejecutables" in capsys.readouterr().out


def test_result_reconciliation_records_review_hash_and_never_accepts_pass(tmp_path, monkeypatch):
    ledger, state = tmp_path / "missions.json", tmp_path / "state.json"
    monkeypatch.setattr(queen, "MISSION_CONTROL", ledger)
    monkeypatch.setattr(queen, "STATE_PATH", state)
    missions = queen.get_missions()
    missions[0].update({"task": "Revisar contrato.", "status": "ASSIGNED", "assigned": True})
    queen.save_json(ledger, {"schema": "COLMENA_MISSION_CONTROL_V1", "total": 179, "missions": missions})
    evidence = tmp_path / "evidence.json"
    evidence.write_text(json.dumps({
        "mission_id": "M0001", "agent_id": "agent-001",
        "status": "REVIEW_REQUIRED", "response": "Informe generado."
    }), encoding="utf-8")
    recorded = queen.record_result(evidence)
    assert recorded["status"] == "REVIEW_REQUIRED"
    assert recorded["evidence_sha256"]
    saved = queen.get_missions()[0]
    assert saved["status"] == "REVIEW_REQUIRED" and saved["assigned"] is False
    persisted = json.loads(state.read_text(encoding="utf-8"))["last_agent_execution"]
    assert persisted["provider"] == "local-ollama"
    assert persisted["evidence_sha256"] == recorded["evidence_sha256"]
    assert persisted["review_required_before_pass"] is True

    evidence.write_text(json.dumps({
        "mission_id": "M0001", "agent_id": "agent-001", "status": "PASS"
    }), encoding="utf-8")
    try:
        queen.record_result(evidence)
    except ValueError as exc:
        assert "PASS" in str(exc)
    else:
        raise AssertionError("La Reina no debe aceptar PASS certificado por el modelo")


def test_result_reconciliation_rejects_unassigned_and_wrong_agent(tmp_path, monkeypatch):
    ledger = tmp_path / "missions.json"
    monkeypatch.setattr(queen, "MISSION_CONTROL", ledger)
    missions = queen.get_missions()
    evidence = tmp_path / "evidence.json"
    evidence.write_text(json.dumps({
        "mission_id": "M0001", "agent_id": "agent-001", "status": "REVIEW_REQUIRED"
    }), encoding="utf-8")
    try:
        queen.record_result(evidence)
    except ValueError as exc:
        assert "no está asignada" in str(exc)
    else:
        raise AssertionError("No debe registrar evidencia de una misión no asignada")

    missions[0].update({"task": "Tarea concreta", "status": "ASSIGNED", "assigned": True})
    queen.save_json(ledger, {"schema": "COLMENA_MISSION_CONTROL_V1", "total": 179, "missions": missions})
    evidence.write_text(json.dumps({
        "mission_id": "M0001", "agent_id": "agent-equivocado", "status": "REVIEW_REQUIRED"
    }), encoding="utf-8")
    try:
        queen.record_result(evidence)
    except ValueError as exc:
        assert "no coincide" in str(exc)
    else:
        raise AssertionError("No debe aceptar evidencia de otro agente")


def test_reassign_blocked_rejects_nonblocked_and_taskless_missions(tmp_path, monkeypatch):
    ledger = tmp_path / "missions.json"
    monkeypatch.setattr(queen, "MISSION_CONTROL", ledger)
    monkeypatch.setattr(queen, "STATE_PATH", tmp_path / "state.json")
    missions = queen.get_missions()
    missions[0].update({"task": "Tarea concreta", "status": "ASSIGNED", "assigned": True})
    queen.save_json(ledger, {"schema": "COLMENA_MISSION_CONTROL_V1", "total": 179, "missions": missions})
    try:
        queen.reassign_blocked("M0001")
    except ValueError as exc:
        assert "BLOCKED" in str(exc)
    else:
        raise AssertionError("No debe reabrirse una misión que no esté BLOCKED")

    missions = queen.get_missions()
    missions[0].update({"task": "", "status": "BLOCKED", "assigned": False})
    queen.save_json(ledger, {"schema": "COLMENA_MISSION_CONTROL_V1", "total": 179, "missions": missions})
    try:
        queen.reassign_blocked("M0001")
    except ValueError as exc:
        assert "sin tarea concreta" in str(exc)
    else:
        raise AssertionError("No debe reabrirse una misión sin tarea")



def test_agent_loads_all_25_canonical_engineering_controls():
    contract = agent.load_mandatory_contract()
    assert "AGENTS.md" in contract
    assert "CONTRATO_MAESTRO_IA.md" in contract
    assert "ENGINEERING_CHARTER.md" in contract
    assert "ENGINEERING_ENFORCEMENT_MATRIX.md" in contract
    matrix = (ROOT / "docs/ENGINEERING_ENFORCEMENT_MATRIX.md").read_text(encoding="utf-8")
    rows = {row for row in range(1, 26) if f"| {row:02d} |" in matrix}
    assert rows == set(range(1, 26))
    assert "Principio" in (ROOT / "docs/ENGINEERING_CHARTER.md").read_text(encoding="utf-8")


def test_agent_system_prompt_enforces_boy_scout_rule_and_safe_retirement():
    source = (ROOT / "scripts/colmena_agent_ollama.py").read_text(encoding="utf-8")
    assert "regla boy scout" in source
    assert "tras revisar referencias" in source
    assert "añade regresión para cada bug" in source
    assert "load_mandatory_contract()" in source
    assert '"num_ctx": 24576' in source



def test_mandatory_contract_loader_fails_closed_when_contracts_are_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(agent, "ROOT", tmp_path)
    try:
        agent.load_mandatory_contract()
    except ValueError as exc:
        assert "falta el contrato obligatorio" in str(exc)
    else:
        raise AssertionError("La inferencia debe bloquearse si faltan las normas canónicas")
