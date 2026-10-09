# COALICIÓN — análisis de decisiones de la demo 2023

```bash
python scripts/demo_multiparty.py
python scripts/demo_decision_analysis.py
pytest -q tests/test_demo_multiparty.py tests/test_demo_decision_analysis.py
```

- JSON auditable: `artifacts/demo_decision_analysis_2023.json`.
- Informe ejecutivo: `reports/demo_decision_analysis_2023.md`.
- Reutiliza `src.electoral.allocate`; no duplica D’Hondt.
- Documenta cambios por candidatura, cociente marginal y coste de oportunidad de agrupar listas.
- La frontera de viabilidad calcula votos adicionales mínimos con votos rivales fijos; el total válido aumenta con los votos añadidos.
- Los hashes de procedencia se incluyen en el JSON y el informe.
- No modela transferencias, participación futura ni conducta electoral. No es predicción ni certificación oficial.
