import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import colmena_queen_hf as queen
import colmena_agent_hf


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
