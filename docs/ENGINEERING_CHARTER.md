# Carta de ingeniería COALICIÓN — 25 principios operativos

**Estado:** normativa obligatoria para IA, agentes, personas y automatizaciones.  
**Aplicación:** código, datos, infraestructura, Git, CI/CD, APIs y operación.  
**Jerarquía:** complemento de `AGENTS.md` y `CONTRATO_MAESTRO_IA.md`; ante conflicto, detener y escalar.

Estos principios son criterios de diseño, no promesas de perfección matemática ni excusas para introducir complejidad. Cada decisión debe ser proporcional al riesgo, verificable y compatible con la arquitectura existente.

## Nivel I — Calidad profesional

1. **Legibilidad antes que ingenio.** Nombres explícitos, funciones comprensibles, efectos secundarios visibles y comentarios que expliquen el porqué.
2. **Automatizar lo repetible.** Automatizar formato, lint, pruebas, auditorías y despliegues cuando el beneficio y el riesgo estén evaluados. Infraestructura como código cuando sea aplicable.
3. **Pruebas como requisito de integración.** Pruebas unitarias, integración, contratos y E2E según riesgo. Cada bug corregido debe tener una regresión cuando sea viable. Ninguna prueba se elimina para ocultar un fallo.
4. **Responsabilidad única y límites claros.** Módulos cohesionados, interfaces pequeñas y dependencias explícitas. No dividir en microservicios por moda.
5. **Diseñar para el fallo.** Timeouts, límites, reintentos con backoff, circuit breakers cuando proceda, degradación controlada e idempotencia en operaciones repetibles.
6. **Seguridad desde el diseño.** Menor privilegio, validación de entradas, protección de secretos, dependencias revisadas, autorización explícita y límites de confianza.
7. **Medir antes de optimizar.** Usar perfiles, métricas, trazas y pruebas de carga reproducibles. Optimizar cuellos de botella observados sin sacrificar corrección.
8. **Tecnología al servicio del problema.** Preferir tecnologías mantenibles y soluciones existentes; encapsular dependencias externas detrás de interfaces solo cuando reduzca acoplamiento real.
9. **Siempre integrable y listo para desplegar.** CI, artefactos reproducibles, configuración separada del código, migraciones seguras, feature flags cuando aporten valor y rollback probado.
10. **Mejora continua sin cuotas artificiales.** Reducir deuda técnica continuamente según riesgo. Limpiar el área tocada sin ampliar innecesariamente el alcance; no imponer porcentajes universales de tiempo.

## Nivel II — Resiliencia y operación

11. **Autorreparación segura.** Detectar, diagnosticar, recuperar y verificar. Las reparaciones automáticas deben tener límites, idempotencia, trazabilidad y mecanismo de parada; no autorizar cambios destructivos sin control.
12. **Chaos engineering con límites.** Solo en entornos aislados o experimentos expresamente autorizados, con hipótesis, radio de impacto, monitorización, abortos y rollback. No inyectar fallos aleatorios en producción por defecto.
13. **Inmutabilidad donde aporta garantías.** Desplegar artefactos versionados e inmutables cuando sea viable. Mantener datos auditables y copias verificadas; usar event sourcing solo si el dominio lo justifica, no como obligación universal.
14. **Latencia como atributo medible.** Establecer SLO/umbrales, medir percentiles y eliminar esperas innecesarias. Caché y asincronía solo con invalidación, consistencia, límites y observabilidad definidos.
15. **Gobierno arquitectónico automatizado.** Comprobar contratos, dependencias, licencias y vulnerabilidades en CI. Bloquear por reglas explícitas y accionables; documentar excepciones temporales.
16. **Observabilidad estructurada.** Logs estructurados y redactados, métricas y trazas correlacionables. Nunca registrar secretos o datos personales innecesarios; alertar por impacto al usuario y SLO, no solo por infraestructura.
17. **Contratos de API evolutivos.** Compatibilidad hacia atrás, versionado cuando haga falta, pruebas de contrato y estrategia de retirada documentada.
18. **Simplicidad operativa.** Entorno reproducible, onboarding breve, comandos canónicos, dependencias declaradas y runbooks accionables. No añadir plataformas que aumenten carga operativa sin beneficio probado.
19. **Decisiones registradas.** ADRs para decisiones arquitectónicas relevantes: contexto, alternativas, decisión, consecuencias y condiciones de revisión.
20. **Postmortems sin culpabilizar.** Investigar condiciones técnicas y del proceso, registrar impacto y convertir los fallos relevantes en acciones verificables y pruebas de regresión.

## Nivel III — Diseño para longevidad

21. **Hacer fácil lo correcto.** Tipos, APIs, esquemas y validaciones deben rechazar estados inválidos lo antes posible; evitar interfaces ambiguas y efectos ocultos.
22. **Compatibilidad como contrato explícito.** Preservar interfaces públicas cuando sea razonable. Todo cambio incompatible requiere versionado o migración, aviso, pruebas y plan de reversión.
23. **Minimalismo radical con evidencia.** Evitar capas, abstracciones, servicios y dependencias innecesarias. No confundir menor número de líneas con mejor diseño; priorizar comprensión y coste total.
24. **Mínima sorpresa y determinismo.** Convenciones consistentes, errores explícitos, orden estable y resultados reproducibles cuando el contrato lo exige. Aleatoriedad solo con semilla y propósito declarados.
25. **Utilidad y responsabilidad.** Diseñar para accesibilidad, privacidad, seguridad, neutralidad, interoperabilidad y beneficio duradero; documentar límites reales y evitar promesas no demostradas.

## Protocolo de aplicación
Para cada cambio: **inspeccionar → identificar causa raíz → plan mínimo → implementar → probar → revisar diff → registrar → validar CI → integrar**. Cada paso deja evidencia proporcional al riesgo.

- Un commit representa una unidad lógica; no existe una cuota ideal de commits ni una equivalencia entre cantidad de commits y calidad.
- No se hace push manual directo a `main`; se usan ramas y PR con checks requeridos.
- La automatización no puede pisar trabajo activo, ocultar fallos ni certificar su propia reparación sin comprobaciones independientes.
- El despliegue se considera correcto solo con evidencia del entorno destino, verificación posterior y rollback viable.
- Las métricas DORA se interpretan como tendencias de entrega y estabilidad, nunca como objetivos aislados que incentiven atajos.
- Ninguna regla exige una tecnología concreta por moda. Si un principio no es aplicable, documentar brevemente el motivo y la alternativa segura.

**Regla de cierre:** no afirmar “perfecto”, “infalible” o “100 % autorregulado”. Informar qué se comprobó, con qué evidencia y qué queda pendiente.
