from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_legacy_huggingface_runtime_files_are_retired():
    """No executable HF integration remains after the Ollama-only migration."""
    retired = (
        ROOT / ".github/workflows/colmena_hf_agents.yml",
        ROOT / ".github/workflows/colmena_hf_assign.yml",
        ROOT / ".github/workflows/colmena_hf_tests.yml",
        ROOT / "scripts/colmena_agent_hf.py",
        ROOT / "scripts/colmena_queen_hf.py",
        ROOT / "tests/test_colmena_hf_agents.py",
        ROOT / "docs/COLMENA_HF_AGENTS.md",
    )
    present = [str(path.relative_to(ROOT)) for path in retired if path.exists()]
    assert not present, f"Runtime legado que debe retirarse: {present}"


def test_colmena_invocation_document_has_real_markdown_line_breaks():
    text = (ROOT / "docs/INVOCACION_COLMENA.md").read_text(encoding="utf-8")
    assert "\\n\\n" not in text, "La documentación contiene secuencias \\\\n literales en lugar de saltos de línea."
    assert "## Agentes IA locales Ollama\n\n" in text


def test_ollama_docs_make_provider_and_evidence_limits_explicit():
    text = (ROOT / "docs/COLMENA_OLLAMA_AGENTS.md").read_text(encoding="utf-8").lower()
    assert "único backend" in text
    assert "no requiere tokens" in text
    assert "nunca empuja directamente a `main`" in text
    assert "no se intenta ningún proveedor remoto" in text
