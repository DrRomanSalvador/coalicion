# COALICIÓN — demo multiparty 2023

## Objetivo
Comparar candidaturas observadas y agrupaciones hipotéticas en Madrid y Barcelona con datos canónicos de las elecciones generales de 2023.

## Ejecutar
```bash
python scripts/demo_multiparty.py
pytest -q tests/test_demo_multiparty.py
# Resultado generado: artifacts/demo_multiparty_2023.json
```

## Escenarios
1. Fragmentado: reproduce y contrasta el reparto observado.
2. Izquierda sin PSOE/PSC: agrupación hipotética especificada en el JSON.
3. Bloque amplio con PSOE/PSC: agrupación hipotética especificada en el JSON.

## Método y límites
- Reutiliza `src.electoral.allocate` y `src.coalition.coalition_decision`; no duplica D’Hondt.
- Agrupa exclusivamente votos observados de candidaturas reales; no inventa votos ni transferencias.
- No predice cambios de comportamiento, participación ni trasvases electorales.
- Valida procedencia, esquema, hash del blob canónico, votos válidos, blancos y escaños observados.
- Si los datos no cuadran o el motor electoral bloquea un empate, aborta sin resultados parciales.
- La simulación contrafactual no es un resultado electoral oficial.
