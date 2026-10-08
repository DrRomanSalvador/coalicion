# Auditoría adversarial de COALICIÓN — 2026-10-08

## Alcance

Auditoría adversarial independiente sobre el circuito de métricas CIS, OOS, predicción, SEEC, ingestión de encuestas y decisión.

Objetivo: intentar demostrar que el sistema **no** merece certificación completa mediante búsqueda de:
- fuentes duplicadas o hardcodeadas;
- fugas temporales;
- mezcla de métricas semánticamente distintas;
- normalizaciones o imputaciones silenciosas;
- denominadores electorales incorrectos;
- evidencia no verificable;
- estados PASS que no prueban lo que declaran.

## Hallazgos

### A-001 — CRÍTICO — CIS 2023 hardcodeado en producción SEEC

**Archivo:** `scripts/run_seec_production.py`

El ejecutor de producción define directamente `SURVEY = {...}`, incluyendo CIS 3411/2023, en vez de leer `artifacts/data/cis_historical_2004_2023.csv` mediante `src/cis_history.py`.

**Riesgo:** existe una segunda fuente de verdad para una métrica que se acaba de declarar canónica. Una modificación del dataset canónico no necesariamente modifica la ejecución SEEC.

**Criterio adversarial:** FAIL hasta eliminar el bloque hardcodeado y conectar SEEC exclusivamente mediante el adaptador canónico, con identificación inequívoca de estudio/fecha/fuente.

### A-002 — ALTO — Denominador OOS no demuestra votos válidos

**Archivo:** `src/oos_pipeline.py`, función `_official()`

El denominador nacional acumula todos los valores de la columna `votos` sin una regla explícita que excluya votos nulos y determine exactamente qué categorías forman el denominador de porcentaje electoral.

**Riesgo:** el porcentaje real usado como `actual` puede diferir del porcentaje válido publicado, especialmente si existen nulos/blancos u otras categorías.

**Criterio adversarial:** FAIL hasta definir y probar el denominador legal/canónico para cada elección y excluir explícitamente categorías que no correspondan.

### A-003 — ALTO — Integridad criptográfica no es parte del cargador CIS

**Archivo:** `src/cis_history.py`

El cargador valida esquema, cobertura, rango y dominio de URLs, pero no verifica el SHA-256 esperado del archivo.

**Riesgo:** un archivo con el mismo esquema y datos plausibles podría sustituir el artefacto materializado sin que el cargador lo detecte.

**Criterio adversarial:** FAIL para certificación de evidencia primaria hasta incorporar manifest/hash o un mecanismo equivalente de integridad reproducible.

### A-004 — MEDIO — El adaptador CIS convierte directamente a OOS sin conservar campos CIS completos

`as_oos_rows()` conserva fecha, partido, estimación, fuente y estudio, pero elimina del circuito OOS `vote_direct_pct` y `seat_range`.

**Riesgo:** es correcto no usar métricas no necesarias, pero la pérdida es irreversible en esa interfaz y facilita confundir intención directa con estimación CIS en consumidores posteriores.

**Criterio:** el contrato debe declarar explícitamente qué métrica consume OOS y mantener disponible la procedencia/metadatos completos en el artefacto de evidencia.

### A-005 — MEDIO — Cobertura del cargador no prueba completitud por estudio

`cis_history.load()` exige las ocho elecciones, pero no exige un conjunto mínimo/esperado de estudios por elección ni valida que cada estudio tenga las mismas reglas de publicación.

**Riesgo:** un artefacto podría conservar ocho etiquetas electorales pero perder silenciosamente estudios o partidos.

**Criterio:** añadir invariantes de cobertura y un manifest de conteos por elección/estudio.

### A-006 — MEDIO — SEEC reconstruye conteos desde porcentajes publicados

`src/seec_bayesian.py` usa `_survey_counts()` y reconstrucción determinista por largest remainder cuando solo dispone de porcentajes y tamaño muestral.

**Riesgo:** no son microdatos observados. La reconstrucción es una transformación modelada, no evidencia de respuestas individuales.

**Criterio:** debe quedar etiquetada como reconstrucción determinista y nunca presentarse como microdato. Para certificación estadística fuerte, preferir conteos/ficha primaria si están disponibles.

### A-007 — BAJO — El monitor y la historia CIS tienen rutas de datos distintas

El monitor operativo usa `survey_watch.json`/feeds y `poll_ingest.py`, mientras la historia CIS canónica usa un artefacto histórico independiente.

**Riesgo:** aceptable por separación temporal/operativa, pero exige una frontera explícita para impedir que dos representaciones de la misma encuesta sean tratadas como observaciones independientes.

**Criterio:** deduplicación por identificador de estudio + fuente + fecha + partido cuando una encuesta pueda aparecer en ambos circuitos.

## Controles que sí superan la revisión estática

- `src/cis_history.py` rechaza esquema incompleto.
- Rechaza observaciones duplicadas por `(election, study_id, party)`.
- Rechaza `source_type` distinto de `PRIMARY_CIS`.
- Rechaza métricas fuera de [0,100].
- Rechaza URLs fuera de `https://www.cis.es/`.
- Exige las ocho elecciones históricas declaradas.
- OOS rechaza observaciones con `field_end >= election_date`.
- OOS implementa walk-forward con entrenamiento exclusivamente en elecciones anteriores.
- SEEC falla cerrado ante composiciones incompletas.
- SEEC exige una única `field_date` por encuesta.
- El informe de encuestas declara explícitamente modo descriptivo y bloquea proyección territorial sin matriz válida.
- El centro de decisión exige 52 circunscripciones y 350 escaños cuando `strict_territory=True`.

## Veredicto adversarial

**NO CERTIFICADO.**

La arquitectura tiene controles relevantes, pero la auditoría adversarial demuestra al menos tres bloqueos materiales antes de poder afirmar certificación completa:

1. eliminar la segunda fuente CIS hardcodeada de SEEC;
2. fijar y verificar el denominador oficial de votos válidos en OOS;
3. incorporar integridad criptográfica/manifest al límite de evidencia CIS.

La auditoría se considera **materializada como evidencia de bloqueo**, no como certificado positivo.

## Regla de cierre

No se debe cambiar este documento a `PASS/CERTIFICADO` por la mera existencia de tests verdes. Cada hallazgo debe cerrarse con código, prueba reproducible y evidencia materializada que pruebe específicamente el contrato afectado.
