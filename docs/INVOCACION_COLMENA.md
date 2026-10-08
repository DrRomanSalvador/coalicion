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
4. Recuperar `artifacts/colmena/queen_state.json`, `queen_approval.json` y evidencias.
5. Continuar desde la primera misión no-PASS.
6. No repetir trabajo ya probado.
7. Solo `DrRomanSalvador/coalicion`, solo `main`.
8. Fail-closed: sin evidencia persistente, no PASS.
9. Cada aprendizaje estructural se codifica en GitHub antes de continuar.
10. **No prueba final hasta resolver las 179 limitaciones.**

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

## NO CONFUNDIR

Las **179** son el contrato de misiones/slots lógicos gobernados por la Reina. Solo se llamarán “agentes IA autónomos” cuando exista evidencia real de ejecución autónoma; el código no inventa esa evidencia.
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

