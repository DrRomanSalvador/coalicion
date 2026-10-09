from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_render_blueprint_declares_decision_demo_service():
    render = (ROOT / "render.yaml").read_text(encoding="utf-8")
    service = render.split("name: coalicion-decision-demo", 1)
    assert len(service) == 2
    config = service[1]
    assert "runtime: python" in config
    assert "buildCommand: python -m compileall -q scripts src" in config
    assert "startCommand: python scripts/demo_decision_server.py --host 0.0.0.0 --port $PORT" in config
    assert "healthCheckPath: /api/health" in config
