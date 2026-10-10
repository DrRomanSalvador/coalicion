#!/usr/bin/env python3
"""Fail CI if the mandatory engineering contract is missing or silently disconnected."""
from pathlib import Path
import re
import sys

from audit_workflow_resilience import workflow_contract_findings

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {
    "AGENTS.md": [
        "## 10. Obligatoriedad y control",
        "## 11. Método de ingeniería de alto nivel",
        "## 12. Métricas de ingeniería y DORA",
        "DETENER",
        "no inventar datos",
    ],
    "docs/ENGINEERING_ENFORCEMENT_MATRIX.md": [
        "## Protocolo obligatorio de PR",
        "causa raíz",
        "cancel-in-progress: true",
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
# Ensure the canonical charter enumerates all 25 principles and the enforcement matrix
# contains one explicit row for each principle. Documentation without coverage is not enough.
charter_path = ROOT / "docs" / "ENGINEERING_CHARTER.md"
matrix_path = ROOT / "docs" / "ENGINEERING_ENFORCEMENT_MATRIX.md"
if charter_path.is_file():
    charter = charter_path.read_text(encoding="utf-8")
    for number in range(1, 26):
        if not re.search(rf"(?m)^{number}\. \*\*", charter):
            errors.append(f"ENGINEERING_CHARTER.md: missing numbered principle {number}")
if matrix_path.is_file():
    matrix = matrix_path.read_text(encoding="utf-8")
    for number in range(1, 26):
        if not re.search(rf"(?m)^\|\s*{number:02d}\s*\|", matrix):
            errors.append(f"ENGINEERING_ENFORCEMENT_MATRIX.md: missing enforcement row {number:02d}")

# Make resilience rules part of the mandatory contract gate, not a separate advisory report.
workflow_dir = ROOT / ".github" / "workflows"
if not workflow_dir.is_dir():
    errors.append("Missing workflow directory: .github/workflows")
else:
    for workflow_path in sorted([*workflow_dir.glob("*.yml"), *workflow_dir.glob("*.yaml")]):
        try:
            workflow_source = workflow_path.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"{workflow_path.relative_to(ROOT)}: unreadable workflow: {exc}")
            continue
        for finding in workflow_contract_findings(str(workflow_path.relative_to(ROOT)), workflow_source):
            errors.append(f"{finding['path']}: {finding['missing_contract']}")
if errors:
    print("ENGINEERING CONTRACT CHECK FAILED")
    print("\n".join(f"- {error}" for error in errors))
    sys.exit(1)
print("ENGINEERING CONTRACT CHECK PASS")
