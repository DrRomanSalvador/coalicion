# COLMENA — REINVOCACIÓN EXACTA

**REPO:** `DrRomanSalvador/coalicion` · **BRANCH:** `main` · **SEED:** `20261006`

## Invocación
Cualquiera de estas frases significa lo mismo:
- **Activa la colmena**
- **Habla la abeja reina**
- **Reinvoca la colmena**
- **Continúa donde quedó la colmena**
- **Recupera el estado de la colmena**

## Regla
El chat es la superficie de invocación. **GitHub es la memoria persistente y fuente de verdad.**

Al ser invocada, la Reina debe:
1. Leer este mapa.
2. Leer `docs/COLMENA_REINVOCACION.json`.
3. Leer `docs/COLMENA_MISSION_CONTROL.json`.
4. Recuperar `artifacts/colmena/queen_state.json`, aprobación y evidencias.
5. Continuar desde la primera misión no-PASS; nunca repetir una misión ya demostrada.
6. Trabajar únicamente en este repositorio y `main`.
7. Fail-closed: sin evidencia no hay PASS.
8. Codificar cada aprendizaje estructural en GitHub para que sobreviva al chat.
9. No declarar agentes autónomos que no estén realmente ejecutándose: 179 es el contrato de 179 misiones/slots lógicos gobernados por la Reina.
10. La prueba final única queda bloqueada hasta resolver las 179 limitaciones.

## Mapa operativo
- Reina: `scripts/colmena_queen.py`
- Worker: `scripts/colmena_worker.py`
- Cierre: `scripts/colmena_closure.py`
- Misiones: `docs/COLMENA_MISSION_CONTROL.json`
- Estado Reina: `artifacts/colmena/queen_state.json`
- Aprobación: `artifacts/colmena/queen_approval.json`
- Evidencia: `artifacts/colmena/worker_*.json`
- Cierre: `artifacts/colmena/colmena_closure.json`

## Estado de continuidad
**PAUSED_FOR_COORDINATION** — no ejecutar la prueba final todavía.

## Recuperación ante pérdida del chat
No pedir al usuario que reconstruya el contexto. Recuperar desde GitHub y continuar. El primer mensaje de otro chat puede ser simplemente: **“Activa la colmena.”**
