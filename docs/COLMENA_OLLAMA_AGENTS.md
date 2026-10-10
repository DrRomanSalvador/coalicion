# Colmena — agentes locales Ollama

La Colmena usa Ollama como único backend de inferencia. No requiere tokens, cuenta de inferencia, créditos ni proveedor externo. Los 179 registros son slots lógicos; no son 179 procesos ejecutándose a la vez.

## Flujo canónico
1. Leer `AGENTS.md`, `CONTRATO_MAESTRO_IA.md` y `docs/COLMENA_STATE.json`.
2. La Reina asigna únicamente misiones con tarea concreta, en lotes de hasta cinco.
3. GitHub Actions instala Ollama, descarga el modelo configurado y ejecuta una misión aprobada.
4. La evidencia queda como `REVIEW_REQUIRED` o `BLOCKED`; el modelo no puede marcar PASS.
5. El workflow propone los cambios de estado/evidencia mediante pull request, nunca empuja directamente a `main`.
6. Un fallo de modelo, timeout o contexto genera evidencia BLOCKED y no se intenta ningún proveedor remoto.

## Ejecución local
```bash
python scripts/colmena_queen.py --status
ollama serve
ollama pull qwen2.5:3b
python scripts/colmena_agent_ollama.py M0001 --model qwen2.5:3b
python scripts/colmena_queen.py --record-result artifacts/colmena/agents/agent-001_M0001.json
```

La misión debe estar asignada explícitamente en `docs/COLMENA_MISSION_CONTROL.json`. El resultado del modelo requiere revisión independiente. La ejecución del agente genera análisis y evidencia; no modifica por sí misma el código fuente del producto.

## GitHub Actions y coste
Usar **COALICIÓN — Agentes locales Ollama** en Actions. El runner estándar de un repositorio público y el software Ollama no requieren créditos de inferencia externos. El modelo se descarga/cacha en el runner; el tiempo y memoria siguen siendo limitados, por lo que un modelo pequeño como `qwen2.5:3b` es el valor inicial. Si la descarga o inferencia falla, el trabajo queda bloqueado y no cambia automáticamente a un proveedor de pago.

## Estados
- `PENDING`: sin asignación.
- `ASSIGNED`: asignación aprobada por la Reina.
- `REVIEW_REQUIRED`: informe producido, pendiente de revisión.
- `BLOCKED`: no se pudo ejecutar o falta evidencia.
- `PASS`: reservado a pruebas/verificación independiente, nunca a la respuesta del modelo.

No se considera persistida una evidencia hasta que su pull request y commit sean visibles en GitHub.
