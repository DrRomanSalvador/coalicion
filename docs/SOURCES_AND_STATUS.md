# Fuentes, estado y límites

## Fuentes primarias congeladas
1. Real Decreto 806/2026, BOE-A-2026-20742, publicado 06-10-2026.
2. LOREG, Ley Orgánica 5/1985, versión vigente.
3. Resultados oficiales 23J 2023, Junta Electoral Central/BOE-A-2023-18907.
4. Ministerio del Interior — Resultados Electorales.
5. Encuestas 2026: fuente primaria, publicación, campo, muestra, modo, voto y escaños publicados.

## Estado verificado — 2026-10-09
- Magnitudes 2026: AUDITADAS contra BOE; `data/2026_circunscripciones_oficiales.csv` valida 52 circunscripciones y 350 escaños.
- Motor legal: IMPLEMENTADO en `src/electoral.py`; no se habilita una segunda implementación de D’Hondt.
- Workbook oficial del Interior: materializado en `data/raw/Elecciones-Congreso.xlsx`; SHA-256 `dba3394f1812f338067231bce68acf56af1e13ddf8cfb709a814bcc46357ebc2`.
- Histórico oficial: `data/official_interior_congreso_1977_2023.csv`, 16 elecciones, 52 circunscripciones, 322556 registros normalizados; manifest `data/manifests/official_interior_congreso.json`.
- Matriz oficial de 2023 partido×circunscripción: MATERIALIZADA en `artifacts/data/election_2023_canonical.json`; validación: 52 circunscripciones, 350 escaños, candidaturas 24487414, blancos 200673, válidos 24688087.
- SEEC de producción: PASS con 10000 draws; cuatro cadenas; diagnósticos sobre `eta` latente incluidos; 0 divergencias; R-hat máximo 1.00; ESS bulk/tail mínimos 1900/3000.
- Calibración OOS: PASS con evidencia persistida en `ci_evidence/oos_calibration.json`.
- Cobertura de transporte de fuentes configuradas: PASS; no equivale a tener todos los sondeos validados.
- Encuestas territoriales generales 2026: no existe todavía una matriz explícita validada de las 52 circunscripciones.
- Territorialización reproducible 2026: BLOQUEADA sin observaciones territoriales comparables; se prohíbe inferir provincias desde porcentajes nacionales.
- Certificación: `READY_FOR_EXTERNAL_AUDIT`, no certificación independiente.
- Release `v1.0.0`: BLOQUEADO hasta auditoría externa independiente y cierre de los bloqueos territoriales/contractuales.

## Regla de publicación
Mientras falte cualquier dato esencial, el proyecto solo puede declarar AUDITADO CON LIMITACIONES, nunca 100% auditado ni resultado definitivo.


## Bibliografía oficial estructurada

La bibliografía canónica de procedencia queda integrada en `docs/BIBLIOGRAFIA_OFICIAL_ESTRUCTURADA.md`.

### Jerarquía de evidencia
- **PRIMARY:** Interior, JEC, BOE, CIS, INE y organismos electorales territoriales competentes.
- **LEGAL:** BOE y normativa electoral vigente.
- **METHODOLOGICAL:** fichas técnicas, microdatos y documentación metodológica oficial.
- **SECONDARY:** medios/agregadores; solo descubrimiento o contraste.
- **AUXILIARY:** contexto y validación cruzada.

### Trazabilidad obligatoria
Cada dato materializado debe conservar, cuando exista: `source_id`, URL, organismo, tipo, fechas, versión/identificador, `sha256`, transformación, ámbito territorial, nivel de evidencia, validación e incidencias.

### Regla crítica
La presencia de una fuente en la bibliografía no implica que sus datos estén ya materializados en `data/` ni conectados al pipeline. El estado de certificación no cambia hasta completar esa materialización y validación reproducible.

### Regla de precedencia
Ante discrepancias, prevalece la fuente oficial competente por autoridad, fecha y ámbito. No se promedian discrepancias ni se sustituyen fuentes primarias por medios.

