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
Los despliegues reales deben crear un objeto GitHub Deployment con el entorno exacto `production` y publicar sus estados. Si Cloudflare u otro destino se despliega sin registrar estos objetos/statuses en GitHub, el informe marcará datos insuficientes; no inventará ceros. La instrumentación del despliegue debe ser añadida y probada en su workflow real antes de interpretar los resultados como DORA completos.

## Lectura correcta
- Sin despliegues en la ventana: frecuencia = 0 solo si el endpoint se consultó correctamente; las demás métricas quedan `null`/insuficientes cuando no existe denominador.
- Sin fecha de commit accesible: el despliegue no entra en el cálculo de lead time y se cuenta la exclusión.
- Un estado fallido no necesariamente implica impacto al usuario; el CFR calculado aquí es un proxy basado en estados de despliegue.
- La recuperación estimada usa el siguiente éxito posterior a un fallo; si no existe, no se inventa tiempo de recuperación.
- Reportar la ventana, muestra, exclusiones, fuente y timestamp. No comparar periodos con instrumentación distinta.
- DORA son métricas de equipo/sistema, no rankings individuales. No aumentar commits, reducir pruebas o evitar despliegues para mejorar artificialmente el indicador.

## Cómo activar medición válida
1. En el workflow que despliega realmente a producción, crear un deployment GitHub para el SHA exacto y el entorno `production`.
2. Publicar estados `in_progress`, `success` o `failure` con el resultado real del proveedor.
3. Conceder únicamente los permisos necesarios `deployments: write` al workflow de despliegue; el informe solo necesita `deployments: read` y `contents: read`.
4. Verificar un despliegue correcto y uno fallido de prueba en entorno seguro, y contrastar manualmente el informe antes de usarlo como referencia operativa.

## Alternativas gratuitas
GitHub Actions + Deployments API es la opción integrada seleccionada para este repositorio. OpenTelemetry es una opción abierta para instrumentar métricas/logs/trazas, pero no calcula DORA por sí solo: requiere almacenamiento, paneles y definir eventos de despliegue/incidente. No se introduce una plataforma externa hasta que exista necesidad y coste operativo justificados.
