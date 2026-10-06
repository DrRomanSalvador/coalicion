from pathlib import Path
import json

ROOT = Path(".")

def test_product_contract_surface_is_present():
    required = [
        "README.md",
        "CONTRATO_MAESTRO_IA.md",
        "docs/INVOCACION_COLMENA.md",
        "docs/COLMENA_STATE.json",
        "docs/CONTRATO_PRODUCTO_COLMENA.md",
        "config/seec_reproducibility.json",
        "src/reproducibility_contract.py",
        "src/colmena_resume.py",
        "src/error_registry.py",
        "docs/ERRORES_CANONICOS.md",
    ]
    assert all((ROOT / p).exists() for p in required)

def test_product_contract_has_single_next_action():
    state = json.loads((ROOT / "docs/COLMENA_STATE.json").read_text(encoding="utf-8"))
    assert isinstance(state["next_single_action"], str)
    assert state["next_single_action"].strip()
