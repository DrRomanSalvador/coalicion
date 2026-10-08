# COALICIÓN — Inteligencia electoral integrada para toma de decisiones

## Propósito

Esta capa convierte la bibliografía oficial y de contraste en un grafo de evidencia reproducible conectado a los motores ya existentes. No crea un segundo D'Hondt, un segundo predictor ni un segundo motor de coaliciones.

Cadena:

FUENTES → EVIDENCIA → INGESTA/VALIDACIÓN → OOS/CALIBRACIÓN → TERRITORIO → ESCAÑOS → MARGINALIDAD → CONTRAFACTUALES → SNAPSHOT DE DECISIÓN → AUDITORÍA

## Registro canónico

config/political_intelligence_sources.json es el registro máquina de la bibliografía integrada.

Interior es la fuente primaria de resultados; JEC/BOE gobiernan proclamaciones y marco legal; INE aporta variables demográficas; CIS aporta encuestas oficiales; las encuestadoras privadas y medios conservan procedencia propia y no sustituyen una fuente primaria.

El registro contiene 16 elecciones generales canónicas hasta 2023. No se incorpora una elección general ficticia de 2023-11-23: la elección general de 2023 fue el 23-07-2023.

## Conexión con el código existente

- src/reproducibility_contract.py: gate de fuente primaria y reproducibilidad.
- src/data.py: frontera de datos.
- src/poll_monitor.py / src/poll_ingest.py: vigilancia e ingestión de encuestas.
- src/oos_pipeline.py: expanding-window OOS.
- src/probabilistic_calibration.py / src/calibration.py: calibración.
- src/prediction.py: capa estadística canónica.
- src/electoral.py: única asignación electoral canónica.
- src/marginality.py: escaños marginales.
- src/coalition.py: contrafactuales de coalición mediante recálculo territorial.
- src/rapid_decision_center.py: snapshot operativo.
- src/electoral_intelligence.py: radar descriptivo y alertas.
- src/evidence_certificate.py: evidencia/certificación.

## Regla de promoción

La existencia de una URL no equivale a que el dato esté materializado. readiness() devuelve BLOCKED hasta que existan las evidencias físicas requeridas.

Estados separados:

REGISTRADO → MATERIALIZADO → VALIDADO → OOS → CALIBRADO → AUDITADO → CERTIFICADO

Nunca se colapsan.

## Evidencias físicas requeridas

- data/official/candidacies/OFFICIAL_2023_CANDIDACY_MATRIX.csv
- 16 archivos OFFICIAL_*_RESULTS.csv en data/official/results/
- data/surveys/
- data/demographics/ cuando se use MRP
- data/certification/ para certificación de caso real

Si falta una evidencia esencial, el sistema no inventa el dato ni lo promueve.

## Uso

python -c "from src.political_intelligence import validate_registry; print(validate_registry())"
python -c "from src.political_intelligence import readiness; print(readiness())"
python -c "from src.political_intelligence import build_evidence_graph; print(build_evidence_graph(as_of='2026-10-08'))"
pytest -q tests/test_political_intelligence.py

## Neutralidad

El sistema produce hechos, evidencia, incertidumbre, escenarios y contrafactuales electorales. No hace persuasión, microtargeting ni recomendaciones partidistas. Una comparación de coaliciones es matemática y contrafactual; no estima voluntad de pacto, negociabilidad ni conducta política futura.
