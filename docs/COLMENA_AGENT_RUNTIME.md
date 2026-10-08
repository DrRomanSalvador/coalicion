# COLMENA — RUNTIME REAL DE 179 AGENTES

## Objetivo

La colmena requiere 179 agentes IA/workers independientes, uno por misión M0001–M0179.

## Proveedor

El proveedor es intercambiable. Puede ser Hugging Face u otro runtime autorizado que pueda demostrar ejecución independiente.

Variables de repositorio:
- COLMENA_AGENT_PROVIDER: identificador del proveedor.
- COLMENA_AI_AGENT_EXECUTION: debe ser exactamente true cuando la ejecución proceda realmente de un agente IA.

Cada job recibe además un COLMENA_AGENT_EXECUTION_ID único formado por ejecución, intento y misión.

## Evidencia obligatoria por agente

Cada evidencia debe contener:
- mission_id
- agent_id = agent-<mission_id>
- agent_runtime.provider
- agent_runtime.execution_id
- agent_runtime.independent = true
- agent_runtime.ai_execution = true
- resultado de la misión
- referencia/commit ejecutado

## Fail-closed

Si el proveedor no está configurado, si no existe un identificador de ejecución o si no puede demostrarse que la ejecución fue realizada por un agente IA independiente, la misión queda BLOCKED.

No se permite convertir 179 jobs, 179 slots lógicos o 179 llamadas al mismo proceso en una afirmación de 179 agentes IA.

## Cierre

La Reina solo puede cerrar la colmena cuando existen las 179 evidencias individuales y todas contienen evidencia válida de runtime independiente IA, además de PASS de misión.

## Reinvocación

Un chat nuevo debe recuperar este contrato, COLMENA_STATE, COLMENA_MISSION_CONTROL, el checkpoint persistido y las evidencias. El chat nunca sustituye la evidencia del runtime.
