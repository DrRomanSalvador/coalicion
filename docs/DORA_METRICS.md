# Métricas DORA gratuitas en COALICIÓN

## Implementación
- Fuente: GitHub Deployments API, usando el token efímero `GITHUB_TOKEN`.
- Ejecución: `.github/workflows/dora-metrics.yml` en GitHub Actions.
- Coste adicional: sin SaaS externo; sujeto a las cuotas y límites de GitHub Actions/API del plan.
- Salida: artefacto `dora-metrics` con `dora_metrics.json` y `dora_metrics.md`; no escribe automáticamente en `main`.
- Ventana predeterminada: 30 días; puede cambiarse con `DORA_WINDOW_DAYS`.

## Cuatro métricas
1. **Deployment frequency:** número de despliegues de producción exitosos en la ventana, expresado también por día.
2. **Lead time for changes:** mediana y promedio de horas entre la fecha del commit desplegado y el momento del despliegue exitoso. Es una aproximación commit→producción, no el tiempo desde que empezó todo el trabajo.
3. **Change failure rate:** despliegues de producción cuyo estado final es `failure` o `error` dividido entre despliegues terminados con estado `success`, `failure` o `error`.
4. **Time to restore service:** mediana y promedio de horas entre el estado fallido de un despliegue y el siguiente despliegue exitoso. Es una aproximación operativa; no sustituye el inicio/fin de un incidente real.

## Condición imprescindible
El workflow `.github/workflows/deploy_telegram_worker.yml` queda instrumentado para crear un objeto GitHub Deployment con entorno exacto `production` y registrar `in_progress`, `success` o `failure` según despliegue y health check. Otros destinos productivos deben añadir la misma instrumentación en su workflow real. Si no hay registros válidos, el informe marcará datos insuficientes; no inventará ceros. La primera ejecución real debe contrastarse con el proveedor antes de considerar la serie completamente verificada.

## Lectura correcta
- Sin despliegues en la ventana: frecuencia = 0 solo si el endpoint se consultó correctamente; las demás métricas quedan `null`/insuficientes cuando no existe denominador.
- Sin fecha de commit accesible: el despliegue no entra en el cálculo de lead time y se cuenta la exclusión.
- Un estado fallido no necesariamente implica impacto al usuario; el CFR calculado aquí es un proxy basado en estados de despliegue.
- La recuperación estimada usa el siguiente éxito posterior a un fallo; si no existe, no se inventa tiempo de recuperación.
- Reportar la ventana, muestra, exclusiones, fuente y timestamp. No comparar periodos con instrumentación distinta.
- DORA son métricas de equipo/sistema, no rankings individuales. No aumentar commits, reducir pruebas o evitar despliegues para mejorar artificialmente el indicador.

## Cómo activar medición válida
1. Verificar que el workflow real registra el SHA y entorno exactos.
2. Publicar estados `in_progress`, `success` o `failure` con el resultado real del proveedor.
3. Conceder únicamente los permisos necesarios `deployments: write` al workflow de despliegue; el informe solo necesita `deployments: read` y `contents: read`.
4. Contrastar el primer despliegue real y su health check con el informe. Probar el camino de fallo en entorno seguro antes de usar el CFR/tiempo de recuperación como serie operativa.

## Alternativas gratuitas
GitHub Actions + Deployments API es la opción integrada seleccionada para este repositorio. OpenTelemetry es una opción abierta para instrumentar métricas/logs/trazas, pero no calcula DORA por sí solo: requiere almacenamiento, paneles y definir eventos de despliegue/incidente. No se introduce una plataforma externa hasta que exista necesidad y coste operativo justificados.
