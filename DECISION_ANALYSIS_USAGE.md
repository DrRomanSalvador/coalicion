# COALICIÓN — demo interactiva de decisiones electorales 2023

## Ejecutar desde la raíz

```bash
python -m pytest -q tests/test_demo_multiparty.py tests/test_demo_decision_analysis.py tests/test_demo_decision_server.py tests/test_demo_decision_ui.py
python scripts/demo_decision_server.py --host 127.0.0.1 --port 8000
```

Abre `http://127.0.0.1:8000/web/demo/`. El servidor materializa el JSON auditable y el informe ejecutivo al arrancar.

## Funciones

- Comparar el reparto observado con los tres escenarios existentes en Madrid y Barcelona.
- Ver escaños marginales, cocientes, coste mecánico de agrupar listas y frontera matemática del siguiente escaño.
- Crear una coalición personalizada eligiendo candidaturas reales de Madrid o Barcelona; el servidor vuelve a calcular con `src.electoral.allocate`.
- Exportar el registro JSON y revisar hashes, fuente, supuestos y límites.
- API local: `GET /api/health`, `GET /api/candidates?region=Madrid`, `GET /api/analysis`, `POST /api/simulate`.

## Integridad y límites

- No duplica D’Hondt; toda asignación usa el motor canónico.
- Las simulaciones agregan votos observados de 2023, conservan votos totales y mantienen fijos los votos de las demás listas.
- No modelan transferencias, participación futura ni conducta electoral: no son predicciones ni probabilidades.
- Se rechazan circunscripciones, candidaturas o selecciones inválidas.
- No constituye certificación oficial independiente.
