from pathlib import Path

def test_docker_is_non_root_and_has_healthcheck():
    text=Path("Dockerfile").read_text(encoding="utf-8")
    assert "USER coalicion" in text
    assert "HEALTHCHECK" in text
