# Búsqueda exhaustiva y resolución de conflictos

## Regla de oro

El sistema debe agotar las fuentes candidatas antes de declarar que un dato no está disponible, pero no debe convertir una URL encontrada en evidencia fiable.

Para resultados electorales oficiales: PRIMARY = Interior/JEC/BOE; SECONDARY = réplicas verificables y medios con datos estructurados; TERTIARY = páginas de referencia o repositorios abiertos.

La fuente primaria oficial prevalece para una celda electoral cuando está disponible.

## Resolución

Resolver siempre significa:
- si existe evidencia suficiente: producir un valor y registrar la evidencia;
- si existe una fuente primaria y difiere de una secundaria: conservar el valor primario y registrar el conflicto;
- si dos fuentes de igual autoridad discrepan sin corrección autoritativa: marcar UNRESOLVED;
- nunca promediar votos oficiales para fabricar una cifra de consenso;
- nunca inventar escaños, votos, candidaturas o provincias.

## Artefactos
- artifacts/exhaustive_search_2023.json
- data/raw/exhaustive/
- artifacts/execution_log.md
- artifacts/audit/

## Ejecución

    python scripts/exhaustive_data_acquisition.py --search --resolve
    MAX_ATTEMPTS=5 RETRY_DELAY=10 bash scripts/run_ai_electoral_engine_robust.sh

## Fuentes oficiales verificadas

El catálogo usa el XLSX de Congreso publicado por el Ministerio del Interior y la resolución oficial de la JEC publicada en BOE para los resultados de 2023. La resolución contiene resultados por circunscripción, votos y escaños, y existe una corrección oficial posterior.

Las fuentes auxiliares permanecen separadas de la evidencia primaria.