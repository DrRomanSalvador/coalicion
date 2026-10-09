# Colmena con inferencia sin créditos de proveedor

## Objetivo

Ejecutar misiones lógicas usando un modelo abierto local en el runner de GitHub Actions, sin llamar a Hugging Face Inference Providers ni requerir `Reina_token` para la inferencia.

## Invocación

1. Abre **Actions → COALICIÓN — Agentes lógicos Hugging Face → Run workflow**.
2. Selecciona la misión ya asignada por la Reina.
3. Selecciona `ollama` como backend (predeterminado).
4. Mantén `qwen2.5:3b` como modelo local, salvo que exista una razón para cambiarlo.
5. Ejecuta una misión de prueba y revisa el artefacto `COLMENA_AGENT_EVIDENCE_V1`.

El workflow instala Ollama, inicia el servicio, descarga el modelo abierto y llama a su API local. En esta ruta no se usa la API de Hugging Face ni su crédito mensual de 0,10 USD. El modelo y sus pesos son gratuitos; la ejecución usa minutos, CPU, RAM y almacenamiento del runner, sujetos a los términos y cuotas vigentes de GitHub Actions.

## Seguridad y límites

- Una sola misión por ejecución; la Reina debe haberla asignado y definido su tarea.
- La respuesta queda en `REVIEW_REQUIRED`, nunca en `PASS` automático.
- Si Ollama falla, la misión queda `BLOCKED`; no hay fallback oculto a un proveedor de pago.
- No se compra crédito ni se habilita facturación automáticamente.
- La caché de modelos reduce descargas repetidas, pero GitHub puede expulsarla o limitarla.
- No se promete capacidad ilimitada ni que un modelo pequeño tenga la misma calidad que un modelo grande alojado.
- El backend `hf` sigue disponible de forma explícita si el usuario decide usar una credencial/proveedor con cuota disponible.

## Comprobación

La prueba focal de `tests/test_colmena_hf_agents.py` simula la API local, verifica que no se necesita `Reina_token` y confirma que el fallo local no dispara inferencia de Hugging Face. La ejecución real debe confirmarse en el check de GitHub Actions; no se considera validada hasta que ese check termine en verde.
