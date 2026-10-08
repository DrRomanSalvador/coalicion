# COALICIÓN v1.0.0

## Estado
**NO RELEASED — BLOQUEADO**

Esta versión no se etiqueta ni se declara estable hasta completar evidencia actual suficiente.

## Implementado
- Sala de situación Telegram.
- Autorización fail-closed y auditoría.
- Evidencia y trazabilidad.
- Monitor de fuentes y alertas.
- Recuperación con reintentos acotados.
- Reproducibilidad por hashes.
- Validación de seguridad, healthcheck y backup.
- Tres observaciones territoriales actuales materializadas.

## Bloqueos de release
- No existe todavía matriz territorial de las 52 circunscripciones para las elecciones generales de 2026.
- No se ejecuta inferencia nacional→provincia.
- La predicción territorial 2026 permanece bloqueada.
- La trazabilidad de algunas fuentes actuales no contiene hash del contenido fuente completo.
- La copia canónica 2023 no está todavía hash-verificada contra el endpoint oficial vivo.

**Regla:** mientras exista cualquiera de estos bloqueos, no se crea `v1.0.0`.
