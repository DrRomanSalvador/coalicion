# COLMENA — MAPA DE REINVOCACIÓN

**REPO:** `DrRomanSalvador/coalicion`  
**BRANCH:** `main`  
**FUENTE DE VERDAD:** GitHub  
**CHAT:** solo superficie de invocación  
**SEED:** `20261006`

## INVOCACIÓN ÚNICA

Estas frases son equivalentes:

> **Activa la colmena**  
> **Habla la abeja reina**  
> **Reinvoca la colmena**  
> **Continúa donde quedó la colmena**  
> **Recupera el estado de la colmena**

## AL RECIBIR CUALQUIERA

1. Leer este archivo.
2. Leer `docs/COLMENA_STATE.json`.
3. Leer `docs/COLMENA_MISSION_CONTROL.json`.
4. Leer `docs/COLMENA_AGENT_RUNTIME.md` y verificar el runtime requerido para los 179 agentes.
5. Recuperar `artifacts/colmena/queen_state.json`, `queen_approval.json` y evidencias.
6. Verificar el runtime y la evidencia de los **179 agentes independientes**.
6. Continuar desde la primera misión no-PASS; si falta evidencia de instanciación o ejecución, esa misión no está cerrada.
7. No repetir trabajo ya probado.
8. Solo `DrRomanSalvador/coalicion`, solo `main`.
9. Fail-closed: sin evidencia persistente, no PASS.
10. No confundir workers lógicos con agentes IA reales.
11. Cada aprendizaje estructural se codifica en GitHub antes de continuar.
12. **No prueba final hasta resolver las 179 limitaciones y verificar los 179 agentes.**

## MAPA EJECUTABLE

| Función | Fuente |
|---|---|
| Reina | `scripts/colmena_queen.py` |
| Dispatcher | `scripts/queen_dispatcher.py` |
| Worker | `scripts/colmena_worker.py` |
| Cierre | `scripts/colmena_closure.py` |
| 179 misiones | `docs/COLMENA_MISSION_CONTROL.json` |
| Estado | `docs/COLMENA_STATE.json` |
| Estado Reina | `artifacts/colmena/queen_state.json` |
| Aprobación | `artifacts/colmena/queen_approval.json` |
| Evidencias | `artifacts/colmena/worker_*.json` |
| Cierre | `artifacts/colmena/colmena_closure.json` |

## PERSISTENCIA

**Repositorio = memoria.**  
Si este chat desaparece, no reconstruirlo desde conversación: leer GitHub, recuperar el último checkpoint y continuar.

**Regla permanente:** `estado → una siguiente acción → ejecutar → evidencia → checkpoint → siguiente acción`.

## PAUSA ACTUAL

**PAUSADO PARA COORDINACIÓN.**  
Los workflows automáticos no deben avanzar la misión mientras la Reina termina de coordinar las 179 limitaciones. La prueba final será única, coherente y posterior al cierre completo.

## CONTRATO REAL DE LOS 179 AGENTES

Las **179 misiones** son 179 unidades de trabajo distintas, identificadas `M0001`–`M0179`. La arquitectura objetivo es **179 agentes IA/workers independientes**, uno por misión, coordinados por la Reina.

Cada agente debe tener identidad única, contexto y alcance propios, aprobación de la Reina, ejecución independiente verificable, evidencia persistente propia y checkpoint recuperable.

El runtime es **agnóstico de proveedor**: puede ser GitHub Actions, Hugging Face u otro runtime autorizado. Lo obligatorio es la evidencia de que los 179 agentes/workers realmente fueron instanciados y ejecutados.

**Corrección crítica:** 179 slots lógicos no equivalen a 179 agentes IA reales. Si el runtime no demuestra los 179 agentes independientes, la Reina mantiene **BLOCKED** y no declara la colmena completada.
## GATE DE CONTINUIDAD

- **Modo persistente:** `PAUSED_FOR_COORDINATION`.
- **No activar workflows nuevos** durante esta fase.
- Leer, auditar, coordinar, corregir documentación/estado y preparar dependencias sí está permitido.
- La ejecución nueva queda reservada para **una única prueba final coherente**, después de resolver las 179 misiones.
- Esta regla está materializada además en `docs/COLMENA_STATE.json` y validada por `src/colmena_resume.py`.

## RECUPERACIÓN EN CHAT NUEVO — MÍNIMO

1. Repositorio: `DrRomanSalvador/coalicion`, rama `main`.
2. Leer este mapa + `docs/COLMENA_STATE.json` + `docs/COLMENA_MISSION_CONTROL.json`.
3. Leer estado/evidencia de Reina si existen; no asumir que una ejecución ocurrió por existir un workflow.
4. Ejecutar `python -m src.colmena_resume`.
5. Tomar **solo** `next_single_action` y respetar el `execution_gate`.
6. Si hay contradicción entre memoria conversacional y GitHub, **manda GitHub**.
7. No reconstruir, repetir ni reinterpretar trabajo ya persistido.
8. Persistir cualquier cambio de estado antes de considerar la continuidad cerrada.

