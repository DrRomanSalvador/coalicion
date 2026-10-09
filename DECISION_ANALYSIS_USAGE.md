# COALICIÓN — análisis y demo interactiva de decisiones 2023

## Ejecutar desde la raíz del repositorio

```bash
python scripts/demo_multiparty.py
python scripts/demo_decision_analysis.py
python -m pytest -q tests/test_demo_multiparty.py tests/test_demo_decision_analysis.py tests/test_demo_decision_ui.py
python -m http.server 8000
```

Abrir `http://127.0.0.1:8000/web/demo/`.

## Entregables

- Interfaz interactiva: `web/demo/index.html`.
- JSON auditable: `artifacts/demo_decision_analysis_2023.json`.
- Informe ejecutivo: `reports/demo_decision_analysis_2023.md`.
- Configuración: `config/demo_multiparty_2023.json`.

## Funciones

- Comparar el reparto observado y cada escenario en Madrid o Barcelona.
- Ver cambios de escaños por candidatura y cocientes marginales disponibles.
- Comparar escaños de miembros por separado con los de la lista agrupada.
- Calcular la frontera matemática de votos adicionales para el siguiente escaño con votos rivales fijos.
- Exportar el registro JSON y revisar procedencia, hashes, supuestos y límites.

## Método y límites

- Reutiliza `src.electoral.allocate`; la interfaz no implementa un segundo motor D’Hondt.
- Agrupa votos observados de 2023 sin inventar transferencias.
- La frontera es un umbral aritmético, no una predicción ni probabilidad.
- Las agrupaciones de candidaturas menores son supuestos, no clasificación oficial.
- No constituye certificación oficial independiente.
- Si falta el JSON, la interfaz informa de la ausencia de datos y no inventa resultados.
