# Colmena — agentes locales Ollama

La Colmena usa Ollama como único backend de inferencia. No requiere tokens, cuenta de inferencia, créditos ni proveedor externo. Los 179 registros son slots lógicos; no son 179 procesos ejecutándose a la vez.

## Decisión de proveedor (revisada el 2026-10-11)

Hugging Face Inference Providers no es una ruta operativa gratuita fiable para esta Colmena: su documentación oficial indica que las cuentas Free reciben **0,10 USD mensuales** en créditos de inferencia, sujetos a cambio; el uso adicional requiere comprar créditos. Ese límite no sostiene una ejecución continua y no se debe depender de él para misiones críticas. Fuente: [Hugging Face — Pricing and Billing](https://huggingface.co/docs/inference-providers/pricing).

Por tanto, no se mantiene una ruta HF ni un fallback remoto oculto. La ruta elegida es Ollama con modelo descargado en el runner de GitHub Actions para repositorio público, o en una máquina local del operador. GitHub documenta que los runners estándar alojados para repositorios públicos no consumen minutos facturables de Actions: [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions). Esto elimina créditos de inferencia, pero no elimina límites de CPU, RAM, descarga, caché o tiempo. Si Ollama no arranca, no encuentra el modelo o agota el tiempo, la misión debe quedar `BLOCKED`; nunca cambiar a un proveedor de pago.

## Contrato de inteligencia obligatorio

Antes de cada inferencia, el agente carga las normas canónicas de `AGENTS.md`, `CONTRATO_MAESTRO_IA.md`, el inicio e índice de `README.md`, `docs/ENGINEERING_CHARTER.md`, `docs/ENGINEERING_ENFORCEMENT_MATRIX.md`, `docs/COLMENA_STATE.json` y la gobernanza de producto. Comprueba que la matriz contiene los 25 principios numerados y que la lista maestra contiene exactamente 430 requisitos originales, con IDs únicos y criterios de aceptación. Si falta un documento, la matriz está incompleta o la lista original no está materializada, la misión queda `BLOCKED`; no se ejecuta el modelo.

La fuente de requisitos está definida en `docs/COALICION_PRODUCT_GOVERNANCE.md` y su índice de control en `docs/COALICION_PRODUCT_REQUIREMENTS_430.json`. El índice está marcado deliberadamente `BLOCKED_SOURCE_LIST_NOT_MATERIALIZED`: la lista exacta anterior no se ha recuperado íntegra dentro del repositorio. **No se inventan 430 requisitos para aparentar cobertura.** Hay que importar la lista original íntegra y comprobarla antes de invocar misiones de producto. Los dominios resumen y el circuito operativo del documento de gobernanza orientan la reconciliación, pero no sustituyen el checklist original.

El prompt de Ollama aplica expresamente la regla boy scout: dejar el área mejor, resolver la causa raíz con el cambio mínimo, reutilizar la lógica heredada que siga aportando valor y eliminar solo lo obsoleto o sin uso tras comprobar referencias. Exige causa raíz, solución, principios afectados, pruebas, resultado verificable, riesgos y rollback. El modelo no puede afirmar que editó archivos o ejecutó pruebas si no lo hizo ni certificar `PASS`.

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
