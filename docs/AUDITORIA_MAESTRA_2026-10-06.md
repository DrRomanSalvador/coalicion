# AUDITORÍA MAESTRA — CORTE 2026-10-06

## Veredicto
**AUDITADO CON LIMITACIONES.**

El núcleo legal/matemático auditado es determinista y usa aritmética racional exacta; la estructura oficial 2026 incorporada contiene 52 circunscripciones y 350 escaños. Se corrigió un defecto real en la detección de empates D'Hondt y se amplió la batería de pruebas. No es posible declarar 100% auditado el sistema completo porque la matriz oficial completa partido×circunscripción 2023, el archivo histórico completo de encuestas, la territorialización reproducible 2026 y la ejecución integral de todo el repositorio aún no están cerrados. **run26.py no existe actualmente en el repositorio.**

## Restricciones verificadas

| Restricción | Estado | Evidencia |
|---|---|---|
| 350 diputados | PASS | LOREG art. 162 + CSV oficial 2026 |
| 52 circunscripciones | PASS | RD 806/2026 + CSV |
| Madrid 38 | PASS | RD 806/2026 |
| Cádiz 8 | PASS | RD 806/2026 |
| Ceuta 1 / Melilla 1 | PASS | RD 806/2026 + LOREG |
| Umbral provincial 3% | PASS | LOREG art. 163 |
| D'Hondt | PASS | LOREG art. 163 + motor |
| Aritmética exacta | PASS | `Fraction`, sin float |
| Desempate por votos totales | PASS | LOREG art. 163 + test |
| Empate absoluto no arbitrario | PASS | motor + test |
| Ceuta/Melilla por mayoría | PASS | LOREG + motor + tests |
| Fusión antes de asignación | PASS | `merge_candidacies` + test |
| Territorialidad inventada | BLOQUEADO | contrato maestro |
| Escaños→% | BLOQUEADO | contrato maestro |
| Corrección OOS obligatoria | PASS | filtro anti-sesgos + contrato |
| run26.py | NO DEMOSTRADO | no existe en el repositorio |

## Hallazgos por gravedad

| Gravedad | Hallazgo | Corrección | Estado |
|---|---|---|---|
| **CRÍTICO** | El sistema completo no puede cerrarse sin matriz territorial oficial 2023 y territorialización reproducible 2026 | Incorporar y validar datos antes de publicar resultado | **ABIERTO** |
| **ALTO** | El detector D'Hondt confundía empate de cociente con empate absoluto cuando los votos totales eran distintos | Corregido; ahora solo bloquea si también existe igualdad absoluta de votos | **PASS** |
| **ALTO** | El backtest 2023 anterior se había descrito como ejecución integral sin existir evidencia ejecutable del pipeline completo | Reclasificarlo como reconstrucción/manual no certificada y exigir ejecución reproducible del parser oficial | **CORREGIDO / NO CERTIFICADO** |
| **ALTO** | Cobertura de pruebas inicialmente insuficiente | Añadidos tests de entradas, umbral, empate, Ceuta/Melilla, conservación y determinismo | **PASS DEL NÚCLEO AISLADO** |
| **MEDIO** | Selección anti-sesgos todavía no está integrada en una evaluación territorial/escaños completa | Requiere scorer conjunto con resultados territoriales reproducibles | **ABIERTO** |
| **MEDIO** | No existe manifest de SHA-256 de todos los artefactos | Añadir al cierre reproducible | **ABIERTO** |
| **MEDIO** | `run26.py` solicitado no existe | No inventarlo; auditar el código realmente presente | **NO DEMOSTRADO** |

## Evidencia electoral

La LOREG establece 350 diputados, mínimo provincial y un diputado para Ceuta y Melilla, y en el art. 163 fija el 3%, la división sucesiva de votos y el desempate por votos totales; el empate absoluto no debe resolverse por nombre de partido. citeturn0search0turn0search9

El RD 806/2026 publicado el 6 de octubre establece las magnitudes de la elección, incluyendo Cádiz 8, Madrid 38, Ceuta 1 y Melilla 1. citeturn0search12

La JEC confirma que los resultados de 2023 publicados en BOE proceden de las actas de escrutinio general y proclamación de electos; el cuadro oficial incluye la matriz por circunscripción de las principales candidaturas y el total estatal de 350 escaños. citeturn1search6turn1search1

El Ministerio del Interior mantiene el conjunto oficial «Resultados Electorales», incluida la distribución XLSX de Elecciones Congreso. citeturn1search0

## Prueba ejecutable

Se ejecutó **solo una reproducción aislada del núcleo electoral** reconstruido desde los archivos actuales, no una ejecución integral del checkout ni del pipeline de ingestión oficial.

Resultado de la reproducción aislada: **10/10 pruebas mínimas PASS**.

Esto demuestra únicamente que esas invariantes del núcleo pasan en el entorno aislado. **No certifica el repositorio completo, no certifica la ingestión 2023 y no certifica el resultado 2026.**

GitHub Actions no proporcionó una ejecución asociada a los commits de esta corrección en el momento de esta auditoría. Por tanto, cualquier afirmación anterior de “PASS integral”, “20/20” o equivalente queda anulada.

## Regla anti-sesgos

Queda incorporada la familia de hipótesis:
**Gobierno × partido × casa × fecha/recencia**, además de no respuesta, recuerdo, ocultación, turnout, modo, dependencia, herding, recencia, eventos, fragmentación, nuevos partidos, coaliciones y efectos territoriales.

Ninguno se convierte en corrección fija por intuición. Solo puede sobrevivir si demuestra generalización fuera de muestra y no deteriora las métricas conjuntas.

## Cierre

El sistema **no debe producir todavía un resultado 2026 presentado como plenamente auditado**. El bloqueo correcto es de datos/territorialización y de cierre reproducible, no del núcleo legal.

La ejecución integral directamente sobre el checkout remoto no pudo completarse porque el entorno de ejecución no resuelve GitHub por red; por ello esta evidencia no se etiqueta como ejecución completa del repositorio.\n\n**Estado maestro: AUDITADO CON LIMITACIONES.**

## Backtest 2023: estado corregido

La comprobación anterior que se describió como “backtest ejecutado sobre las 52 circunscripciones” **no debe considerarse una ejecución reproducible certificada**. Fue una reconstrucción manual/auxiliar de los datos publicados, útil para detectar errores de interpretación (por ejemplo, PSC separado del PSOE en Cataluña y EH Bildu en Navarra), pero no existe en el repositorio una ejecución automatizada que demuestre de extremo a extremo:

1. ingestión de todos los datos oficiales de 2023;
2. matriz completa candidatura × circunscripción;
3. validación de votos válidos;
4. aplicación automática de D'Hondt a las 52 circunscripciones;
5. comparación automática contra los 350 escaños oficiales;
6. registro de hashes y salida reproducible.

Por tanto, el estado correcto es:

**2023 núcleo matemático: TEST AISLADO PASS.**

**2023 pipeline oficial completo: NO DEMOSTRADO.**

**Resultado 2026 plenamente auditado: NO DECLARADO.**

No se conserva ningún “PASS 52/52” anterior como evidencia certificadora hasta que exista una ejecución automática reproducible con sus artefactos.