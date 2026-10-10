# AGENTS.md — Contrato de trabajo para IA y colaboradores

**Ámbito:** todo cambio de código, datos, documentación, Git, CI/CD y automatizaciones de este repositorio.  
**Objetivo:** reducir errores, duplicación, contradicciones, regresiones, obsolescencia y pérdida de trabajo.  
**Prioridad:** este documento complementa —no sustituye ni rebaja— `README.md`, `CONTRATO_MAESTRO_IA.md` y los contratos específicos del área. Si hay conflicto, DETENER y registrar la contradicción.

## 1. Antes de actuar
1. Leer `README.md`, `CONTRATO_MAESTRO_IA.md`, este archivo y el estado operativo aplicable.
2. Confirmar rama, HEAD, estado de trabajo, PR y ejecuciones CI relevantes. Trabajar solo en `DrRomanSalvador/coalicion`, salvo autorización expresa.
3. Localizar la implementación, contrato, pruebas y workflow canónicos antes de crear o modificar nada.
4. Definir el cambio mínimo que resuelve la causa raíz. No adivinar requisitos ni declarar éxito sin evidencia.

## 2. Una sola fuente de verdad
- No duplicar lógica, validaciones, configuración, documentación ni workflows que ya tengan una fuente canónica.
- No añadir parches acumulativos si una corrección coherente o reescritura acotada elimina duplicación y contradicciones con menos cambios.
- Reescribir solo el ámbito necesario: evitar tanto el parche frágil como la reescritura masiva sin justificación.
- Actualizar o eliminar instrucciones obsoletas cuando cambie su fuente de verdad; no dejar versiones contradictorias.
- Buscar usos, dependencias, contratos y pruebas antes de renombrar, mover o borrar archivos o interfaces.
- Ante una contradicción o falta de evidencia crítica: **DETENER → IDENTIFICAR → REGISTRAR → NO PROPAGAR**.

## 3. Cambios y commits
- Cada commit debe representar una unidad lógica coherente, revisable y recuperable.
- Preferir cambios pequeños y atómicos; un cambio que requiere varios archivos puede ir en un solo commit si todos pertenecen a la misma solución.
- No existe un número ideal de commits ni una cuota diaria. La calidad se mide por claridad, trazabilidad, pruebas y facilidad para revisar o revertir; no por cantidad.
- Prohibidos los commits opacos como `updates`, `fixes` o `cambios generales`. Usar mensajes descriptivos; preferir Conventional Commits: `fix: prevent duplicate poll ingestion`, `test: cover missing territorial inputs`, `docs: define AI Git workflow`.
- No mezclar refactorizaciones ajenas, formato masivo y cambios funcionales sin necesidad demostrable.
- No reescribir el historial compartido ni hacer force-push sobre `main`. Antes de actualizar una rama compartida, comprobar su HEAD y proteger los cambios ajenos.
- No escribir directamente en `main` desde trabajo manual de IA: usar rama y PR. Las automatizaciones autorizadas que persistan estado generado son una excepción limitada y deben ser idempotentes, acotadas, concurrentemente seguras y auditables.

## 4. Protocolo obligatorio de cambio
1. **Inspeccionar:** leer el código y sus consumidores; reproducir el fallo o establecer una línea base.
2. **Plan mínimo:** declarar internamente causa raíz, archivos necesarios, riesgo y pruebas pertinentes.
3. **Implementar:** corregir la causa raíz sin duplicar motores, reglas ni configuración.
4. **Probar:** ejecutar primero pruebas focalizadas y después las comprobaciones relevantes más amplias; validar tipos, lint, contratos, datos y determinismo cuando correspondan.
5. **Revisar el diff:** buscar cambios accidentales, secretos, datos inventados, código muerto, mensajes ambiguos, archivos generados innecesarios y documentación desactualizada.
6. **Registrar:** commit claro y PR con problema, solución, pruebas, riesgos y limitaciones.
7. **Verificar integración:** confirmar CI y conflictos contra la base actual. No fusionar con checks requeridos fallidos o pendientes.
8. **Cerrar:** registrar SHA, pruebas observadas, fallos pendientes y una única siguiente acción. No declarar validación, despliegue o autocuración sin evidencia verificable.

## 5. Pruebas y seguridad de la afirmación
- No basta con que el código compile: cubrir comportamiento, casos límite, regresiones y fallos de entradas ausentes o inválidas.
- Los tests deben comprobar resultados y efectos reales, no solo que una función existe o devuelve una estructura superficial.
- No debilitar, eliminar ni saltar una prueba para hacer verde CI sin demostrar que el test era incorrecto y sustituirlo por una comprobación adecuada.
- Nunca simular un PASS, ocultar un error, convertir un estado BLOCKED en éxito ni afirmar que una prueba pasó sin resultado observable.
- Si no se puede ejecutar una prueba, decir exactamente cuál quedó sin ejecutar y por qué.

## 6. Workflows y automatizaciones que respetan el trabajo en curso
El objetivo es evitar interrupciones, carreras, pérdidas y duplicación de trabajo. Ningún sistema puede prometer interrupción cero en toda circunstancia; hay que diseñarlo para minimizarla y recuperarse de forma segura.

- No cancelar una ejecución activa válida para dar prioridad a una nueva: evitar `cancel-in-progress: true` en procesos largos, de estado o de publicación.
- Definir grupos de concurrencia por recurso compartido y una política de cola compatible con GitHub Actions. Comprobar expresamente si las ejecuciones pendientes pueden reemplazarse; no asumir que `cancel-in-progress: false` conserva una cola ilimitada.
- No permitir dos escritores concurrentes del mismo artefacto, rama, base de datos o estado. Usar exclusión mutua, control optimista de versión/HEAD, transacciones o mecanismo equivalente.
- Hacer las tareas idempotentes: reintentar no debe duplicar publicaciones, encuestas, alertas, commits ni efectos externos.
- Aplicar timeout razonable, reintentos limitados con backoff, manejo explícito de errores y checkpoints duraderos. No hacer bucles infinitos ni reintentos agresivos.
- Si una tarea depende de otra, esperar su resultado de forma explícita; no iniciar trabajo dependiente mientras sus entradas estén incompletas.
- Preservar logs y diagnósticos incluso si falla un paso posterior. Separar persistencia de diagnóstico de la decisión final de éxito/fallo.
- No sobrescribir trabajo nuevo con snapshots antiguos. Antes de escribir, actualizar la base y reconciliar el estado; ante conflicto no resoluble, fallar cerrado.
- Usar permisos mínimos, secretos solo desde el almacén seguro y ningún token en logs, artefactos o commits.
- Los workflows deben declarar condiciones, dependencias, timeouts y criterios de éxito. Las ejecuciones manuales, programadas y disparadas por eventos deben convivir sin carreras.
- La autorrecuperación nunca debe ocultar el fallo original ni aprobar su propia reparación sin pruebas independientes de regresión.

## 7. Salud de Git y del repositorio
- Mantener `main` integrable: PR revisable, checks requeridos en verde y sin conflictos antes de fusionar.
- Usar ramas con propósito claro; eliminar ramas temporales fusionadas cuando sea seguro y no sean compartidas por un proceso activo.
- No subir secretos, credenciales, cachés, entornos, archivos temporales, salidas no reproducibles ni grandes artefactos derivados sin necesidad y política explícita.
- No borrar evidencia, historial, manifests, hashes ni checkpoints para “limpiar” el repositorio.
- Actualizar pruebas, documentación, schemas, manifests y workflows afectados en el mismo cambio lógico.
- Mantener dependencias justificadas y fijadas de acuerdo con la política del proyecto; no introducir paquetes por comodidad si ya existe una solución canónica.
- Revisar diferencias y conflictos contra la versión actual de la rama base; no asumir que la base no ha avanzado.

## 8. Datos y reproducibilidad de COALICIÓN
- El repositorio y sus evidencias materializadas son la fuente de verdad; el chat no sustituye el estado versionado.
- Mantener neutralidad, procedencia, hashes, fechas, versiones y parámetros; no inventar datos ni sustituir fuentes silenciosamente.
- No cambiar metodología, reglas electorales, semillas, ventanas OOS ni umbrales sin versionar la decisión, justificarla y añadir pruebas.
- Con entradas esenciales ausentes, contradicción, fallo de invariantes o falta de reproducibilidad: estado bloqueado, sin resultados ficticios.
- Una misma versión con los mismos datos, reglas y parámetros debe producir el mismo resultado cuando el contrato exige determinismo.

## 9. Criterio de aceptación
Un cambio solo está listo cuando:
- resuelve una causa identificada;
- no introduce duplicación ni contradicciones;
- su diff es proporcional y revisable;
- las pruebas pertinentes tienen resultado conocido;
- la documentación y los contratos están alineados;
- CI y la integración están comprobados;
- quedan declarados los riesgos y límites reales.

**Regla final: menos cambios innecesarios, más evidencia; ninguna afirmación sin comprobar.**
