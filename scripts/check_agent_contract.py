#!/usr/bin/env python3
"""Fail CI if the mandatory engineering contract is missing or silently disconnected."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {
    "AGENTS.md": [
        "## 10. Obligatoriedad y control",
        "## 11. Método de ingeniería de alto nivel",
        "## 12. Métricas de ingeniería y DORA",
        "DETENER",
        "no inventar requisitos",
    ],
    "docs/ENGINEERING_CHARTER.md": [
        "## Nivel I — Calidad profesional",
        "## Nivel II — Resiliencia y operación",
        "## Nivel III — Diseño para longevidad",
        "21. **Hacer fácil lo correcto.**",
        "25. **Utilidad y responsabilidad.**",
    ],
    "docs/DORA_METRICS.md": [
        "Deployment frequency",
        "Lead time for changes",
        "Change failure rate",
        "Time to restore service",
        "datos insuficientes",
    ],
    "docs/BRANCH_PROTECTION.md": ["Exigir pull request antes de fusionar", "Bloquear force-push"],
    "docs/REPOSITORY_STRATEGY.md": ["Cuándo mantener un monorepo", "Cuándo considerar multirrepo"],
    ".github/copilot-instructions.md": ["AGENTS.md", "acceptance requirements"],
    "README.md": ["AGENTS.md", "CONTRATO_MAESTRO_IA.md", "ENGINEERING_CHARTER.md", "DORA_METRICS.md", "REPOSITORY_STRATEGY.md", "BRANCH_PROTECTION.md"],
}
errors = []
for relative, markers in REQUIRED.items():
    path = ROOT / relative
    if not path.is_file():
        errors.append(f"Missing mandatory file: {relative}")
        continue
    content = path.read_text(encoding="utf-8")
    for marker in markers:
        if marker.casefold() not in content.casefold():
            errors.append(f"{relative}: missing mandatory marker {marker!r}")
if errors:
    print("ENGINEERING CONTRACT CHECK FAILED")
    print("\n".join(f"- {error}" for error in errors))
    sys.exit(1)
print("ENGINEERING CONTRACT CHECK PASS")
