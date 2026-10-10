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


def test_ollama_failure_is_blocked_and_never_falls_back(tmp_path, monkeypatch):
    from urllib.error import URLError
    ledger = tmp_path / "missions.json"
    monkeypatch.setattr(agent, "MISSION_CONTROL", ledger)
    monkeypatch.setattr(agent, "AGENTS_DIR", tmp_path / "evidence")
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
    assert '(ollama serve > /tmp/ollama.log 2>&1 &)' in source
    assert 'ollama pull "$LOCAL_MODEL"' in source
    assert 'ollama list | grep -F "$LOCAL_MODEL"' in source
