# Protección obligatoria de ramas y CI

Este documento completa `AGENTS.md`. Un workflow en el repositorio no puede forzar por sí solo que GitHub lo exija antes de fusionar. La obligatoriedad técnica necesita reglas de rama/rulesets configuradas en los ajustes del repositorio.

## Configuración requerida para `main`
En GitHub: **Settings → Rules → Rulesets** (o Branches → Branch protection rules), crear una regla activa dirigida a `main`:

- Exigir pull request antes de fusionar.
- Exigir al menos una aprobación independiente cuando exista otro revisor disponible; si el equipo es de una sola persona, mantener checks obligatorios y revisión propia documentada sin fingir independencia.
- Exigir que las aprobaciones sean recientes respecto al último push y descartar aprobaciones obsoletas.
- Exigir resolución de todas las conversaciones de revisión.
- Exigir checks: `Verify mandatory agent contract` y los checks de CI del código afectados por la PR. Seleccionar sus nombres exactos después de que GitHub los haya ejecutado una vez.
- Exigir rama actualizada respecto a `main` antes de fusionar cuando el proyecto y los workflows lo permitan.
- Bloquear force-push y borrado de `main`.
- Aplicar la regla a administradores y bots de escritura; limitar bypass a una excepción explícita, registrada y de emergencia.
- Exigir revisión de CODEOWNERS para los contratos, workflows y controles de seguridad si hay responsables disponibles.
- Mantener secretos fuera del código y conceder a cada workflow solo los permisos mínimos.

## Comprobación de activación
1. Ejecutar una PR de prueba y verificar que los checks aparecen como requeridos, no solo como informativos.
2. Confirmar que una PR que falle el contrato no puede fusionarse.
3. Confirmar que un push directo/force-push a `main` es rechazado para los actores ordinarios.
4. Registrar quién puede hacer bypass y bajo qué procedimiento.
5. Revisar la configuración periódicamente y tras cambios de permisos.

**Limitación actual:** el conector disponible no permite leer ni modificar la protección de ramas (GitHub devuelve 403 al consultar el endpoint). Por tanto, este cambio añade la guía y el check CI, pero no afirma que la protección de `main` haya quedado activada en Settings. Un administrador debe aplicar y verificar los ajustes anteriores.
