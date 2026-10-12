# COALICIÓN — Especificación maestra de capacidades y auditoría

**Estado:** especificación normativa; no implica que las capacidades estén implementadas.
**Propósito:** producto neutral de inteligencia electoral y política para operación continua, periodos de alta actividad, elecciones súbitas, campaña, jornada electoral y seguimiento postelectoral.
**Fuente de requisitos:** especificación maestra aportada por el usuario el 11-10-2026. No reconstruir ni declarar que equivale a una lista histórica de 430 elementos sin reconciliación explícita.

## 1. Contrato de auditoría: tres dimensiones separadas

Cada requisito debe registrar por separado:
1. **CAPACIDAD:** qué debe hacer COALICIÓN.
2. **MONITORIZACIÓN:** qué evento, fuente, condición o cambio debe observar.
3. **VERIFICACIÓN:** qué evidencia de repositorio y ejecución demuestra que funciona.

La existencia de un archivo, clase, workflow, endpoint o prueba unitaria no demuestra por sí sola que una capacidad esté operativa.

### Estados admitidos
- **OPERATIVO:** implementación identificada, fuente/datos reales materializados, ejecución comprobada, prueba relevante superada y evidencia reproducible.
- **PARCIAL:** funciona solo una parte o con límites documentados.
- **BLOQUEADO:** no puede operar de forma segura por falta de datos, credenciales, dependencias o evidencia.
- **NO IMPLEMENTADO:** no existe una implementación demostrable.
- **NO VERIFICADO:** existe indicio de implementación, pero falta prueba suficiente.

### Campos obligatorios de cada fila de auditoría
ID estable; dominio; tipo (CAPACIDAD/MONITORIZACIÓN/VERIFICACIÓN); requisito; prioridad; archivo/flujo responsable; fuente real; datos materializados; prueba automatizada; evidencia de ejecución; limitaciones/fallos; métrica de operación; estado; dependencias; misión responsable; fecha y SHA auditados.

## 2. Inventario de capacidades y controles

### A. Monitorización de fuentes
- BOE, legislación electoral y disposiciones oficiales.
- Ministerio del Interior y resultados electorales oficiales.
- Junta Electoral Central y juntas electorales territoriales.
- INE, censo y estadísticas demográficas pertinentes.
- Congreso, Senado, diarios de sesiones, iniciativas y votaciones.
- Gobierno, ministerios, ruedas de prensa y comunicados.
- Gobiernos y parlamentos autonómicos.
- Partidos nacionales, autonómicos y organizaciones territoriales.
- CIS: barómetros, estudios preelectorales, postelectorales y microdatos.
- Encuestadoras privadas y medios que publican sondeos.
- Agencias de noticias, prensa nacional, regional y local.
- Fuentes públicas sobre candidaturas, financiación, gasto electoral y contratación cuando estén disponibles.
- Fuentes públicas sobre sindicatos, patronales, asociaciones y otros actores relevantes para la agenda política.
- Calendarios de actos, comparecencias, debates y acontecimientos institucionales.
- Descubrimiento automático de nuevas fuentes y detección de fuentes desaparecidas.

**Verificación mínima:** inventario de fuentes versionado; propietario/prioridad; URL y método de captura; frecuencia esperada; última captura correcta; frescura; historial de caída/recuperación; evidencia de una ejecución real por fuente.

### B. Ingesta, calidad y trazabilidad
- Captura recurrente programada con frecuencia configurable por fuente.
- Detección de novedades y cambios en documentos publicados.
- Conservación del original, URL, fecha de publicación y fecha de captura.
- Hash, versión, procedencia y registro de transformaciones.
- Normalización de partidos, coaliciones, personas, instituciones y territorios.
- Detección de duplicados y republicaciones.
- Identificación de rectificaciones y versiones contradictorias.
- Separación de hechos, declaraciones, interpretaciones y estimaciones.
- Validación de formatos, campos, fechas y coherencia de cifras.
- Detección de datos ausentes, caducados o anómalos.
- Reintentos, recuperación y mecanismos alternativos de captura.
- Historial de fallos, recuperaciones y cambios por fuente.
- Indicadores de cobertura y frescura.
- Bloqueo del análisis si faltan datos críticos.

**Verificación mínima:** originales preservados; hash recalculable; pruebas de duplicados, correcciones, anomalías, caída/recuperación y fail-closed; métrica de frescura/cobertura calculada desde ejecuciones reales.

### C. Calendario político y electoral
- Calendario electoral oficial con plazos y fechas límite.
- Censo, reclamaciones y resoluciones.
- Presentación, proclamación e impugnación de candidaturas.
- Formación y registro de coaliciones electorales.
- Convocatoria, precampaña, campaña, jornada de reflexión y votación.
- Debates electorales, entrevistas y comparecencias.
- Encuestas sujetas a publicación y periodo legal de prohibición, cuando corresponda.
- Voto por correo, voto exterior y procedimientos electorales.
- Resultados provisionales y definitivos.
- Escrutinio, reclamaciones y recursos.
- Constitución de las cámaras, consultas e investiduras.
- Plenos, comisiones, votaciones, comparecencias y vencimientos parlamentarios.
- Elecciones autonómicas/locales, mociones de censura, cuestiones de confianza y otros hitos.
- Alertas anticipadas por plazos próximos y tareas incompletas.
- Recálculo automático cuando cambie una fecha oficial.

**Verificación mínima:** cada hito enlazado a fuente primaria y disposición aplicable; zona horaria; fecha de publicación/captura; pruebas de modificación de fechas, vencimiento, festivos, duplicados y avisos escalonados. No convertir fechas de noticias en plazos jurídicos sin evidencia oficial.

### D. Inteligencia de encuestas
- Detección de cada nueva encuesta.
- Extracción de fechas de campo, muestra, método, universo, promotor y publicación.
- Resultados por partido, indecisos, participación y otros indicadores publicados.
- Comparación con sondeo anterior de la misma empresa, otras empresas e histórico.
- Detección de cambios, revisiones y anomalías metodológicas.
- Registro de efectos de casa y diferencias sistemáticas entre encuestadoras.
- Tendencias temporales sin confundirlas con cambios reales de intención de voto.
- Incertidumbre y error muestral explícitos.
- Identificación de encuestas nacionales que no permiten inferencia provincial directa.
- Archivo de datos originales y resultados extraídos para reproducir análisis.
- Seguimiento de cobertura, antigüedad y calidad metodológica por fuente.

**Verificación mínima:** registro bruto inmutable; fechas de campo separadas de publicación; parser probado con fuentes reales; reconciliación de porcentajes; historial de revisiones; backtest fuera de muestra cuando haya predicción; no extrapolar a provincia sin muestra/modelo válido.

### E. Inteligencia política y acontecimientos
- Identificar declaraciones oficiales y atribuirlas a fuente original.
- Detectar anuncios públicos de pactos, rupturas, vetos y negociaciones.
- Seguir cambios de posición programática y compromisos publicados.
- Registrar dimisiones, nombramientos, portavocías y candidaturas.
- Detectar cambios de alianzas parlamentarias y apoyos a iniciativas.
- Seguir votaciones, acuerdos, derrotas y cambios de mayoría.
- Relacionar acontecimientos con partidos, territorios, temas y fechas.
- Detectar contradicciones entre declaraciones públicas de una organización.
- Distinguir declaraciones originales de interpretaciones periodísticas.
- Identificar información confirmada por varias fuentes independientes.
- Detectar noticias corregidas, desmentidos y rectificaciones.
- Mantener cronología de acontecimientos con fuentes.
- Separar hechos confirmados de hipótesis y análisis.
- No presentar rumores, motivaciones supuestas ni publicaciones virales como hechos.

**Verificación mínima:** procedencia primaria enlazada; etiquetas epistemológicas; contradicciones y rectificaciones versionadas; corroboración independiente sin contar republicaciones como fuentes independientes.

### F. Inteligencia territorial
- Base histórica de resultados por partido, elección y circunscripción.
- Resultados municipales cuando existan y sean comparables.
- Participación, votos válidos, blancos, nulos y magnitudes electorales.
- Cambios de límites, denominaciones y candidaturas.
- Encuestas territoriales solo con muestra adecuada.
- Separación de datos medidos y estimaciones modelizadas.
- Circunscripciones donde pequeños cambios alteran escaños.
- Sensibilidad a participación, fragmentación y concentración del voto.
- Comparación histórica teniendo en cuenta cambios de partidos y reglas.
- Prohibición de asignar porcentajes nacionales artificialmente a cada provincia.
- Mapas, tablas y fichas territoriales reproducibles.

**Verificación mínima:** fuente oficial por elección/territorio; cobertura completa declarada; invariantes de votos/escaños; trazabilidad de cambios territoriales; escenarios sin datos inventados.

### G. Motor de escenarios de coalición
- Comparar concurrencia conjunta/separada por circunscripción.
- Comparar composiciones alternativas de listas cuando los datos lo permitan.
- Aplicar reglas electorales vigentes en cada elección.
- Modelar umbrales, magnitud de circunscripción y distribución del voto.
- Mostrar escaños y votos por partido y territorio.
- Calcular diferencias frente a escenario de referencia.
- Detectar dónde cambia la asignación y dónde no.
- Mostrar participación y fragmentación alternativas.
- Incorporar incertidumbre en votos/escaños solo con modelo validado.
- Distinguir simulación mecánica, proyección estadística y dato observado.
- Registrar supuestos; reproducir, comparar y versionar escenarios.
- Mostrar sensibilidad a cada supuesto, no solo escenario central.
- Bloquear resultados con información territorial insuficiente.
- No convertir simulaciones en recomendaciones políticas automáticas.

**Verificación mínima:** pruebas matemáticas independientes del reparto; suma de escaños correcta; supuestos versionados; repetición determinista; comparación contra referencia; incertidumbre calibrada antes de publicarse como probabilidad.

### H. Alertas multicanal
- Telegram como canal operativo inicial.
- Prioridades alta/normal y resúmenes.
- Enrutamiento por tema, territorio, evento y destinatario autorizado.
- Deduplicación, agrupación y control de frecuencia.
- Confirmación de envío y registro de errores.
- Reintentos y cola persistente.
- Escalado de alertas críticas no entregadas.
- Enlaces a fuentes y evidencia en cada alerta.
- Estado de entrega, hora del evento y hora de detección.
- Umbrales, silencios y preferencias configurables.
- Alertas de salud del sistema.
- Historial consultable y motivo de activación.

**Verificación mínima:** envío real a destinatario autorizado; confirmación; deduplicación; retry; recuperación de cola; no revelar secretos; fallo del canal no elimina la alerta.

### I. Centro de decisión e informes
- Briefing diario automático.
- Resumen de últimas horas y próximos hitos.
- Cambios frente al informe anterior.
- Novedades por tema, institución, partido y territorio.
- Encuestas nuevas y evolución histórica.
- Escenarios de coalición comparados.
- Datos caducados, fuentes caídas y conclusiones bloqueadas.
- Evidencia que sustenta cada conclusión.
- Informe urgente bajo demanda.
- Cierre diario y resumen semanal.
- Exportación reproducible y enlaces a fuentes.
- Registro de información disponible al generar el informe.

**Verificación mínima:** generación programada y bajo demanda; referencias a evidencia; comparación de versiones; reproducción con snapshot de datos; limitaciones visibles.

### J. Operación, seguridad y mantenimiento
- Ejecución persistente y programada, no dependiente de intervención manual.
- Monitorización de tareas, colas y retrasos.
- Latencia por fuente y alerta.
- Consumo de recursos y límites de API.
- Secretos y credenciales gestionados de forma segura.
- Control de acceso a canales y destinatarios.
- Copias de seguridad, recuperación e histórico.
- Protección ante documentos maliciosos e instrucciones incrustadas en fuentes externas.
- Auditoría de cambios de configuración.
- Versiones de código, datos y modelos.
- Degradación segura ante fallos externos.
- Panel de estado: operativo, degradado, bloqueado o sin datos recientes.

**Verificación mínima:** ejecución programada observada; alertas de salud; secretos ausentes de logs; pruebas de permisos, backup/restore, inyección de instrucciones y fallo de dependencias.

### K. Validación, auditoría y calidad
- Pruebas unitarias, integración y extremo a extremo.
- Datos históricos conocidos.
- Evaluación fuera de muestra.
- Calibración probabilística si se publican probabilidades.
- Referencias simples y documentadas.
- Falsos positivos y negativos de alertas.
- Caída, recuperación, duplicación y retraso de fuentes.
- Entrega Telegram y recuperación de pendientes.
- Verificación matemática del reparto de escaños.
- Reproducibilidad y consistencia entre versiones.
- Evidencia de pruebas y CI.
- Separación entre pruebas superadas, limitaciones y certificaciones no realizadas.

**Verificación mínima:** SHA exacto de código; resultados reproducibles; fixtures y datos identificados; métricas de calidad; nunca declarar certificación sin evaluación específica independiente.

## 3. Catálogo inicial de alertas

El catálogo normativo de 97 tipos está en `docs/COALICION_ALERT_CATALOG.json`. Es ampliable y configurable: no significa que todos los eventos generen un mensaje inmediato.

## 4. Contrato de contenido de cada alerta

Cada alerta incluye cuando proceda:
- Evento: qué ocurrió.
- Detección: cuándo se detectó y cuándo ocurrió/publicó.
- Fuente: enlace directo, tipo y evidencia preservada.
- Verificación: confirmado, pendiente, contradictorio o corregido.
- Novedad: diferencia frente al estado anterior.
- Ámbito: estatal, autonómico, provincial o municipal.
- Relevancia descriptiva: regla de activación que cumple.
- Impacto analítico: qué se recalculó y qué no.
- Incertidumbre: datos ausentes y supuestos.
- Seguimiento: siguiente fecha, plazo o fuente.
- Trazabilidad: ID de evento, versión de datos y registro de entrega.

## 5. Prioridad de implementación

- **P0 — Operación electoral inmediata:** calendario oficial/plazos, cobertura de fuentes, nuevas encuestas, Telegram fiable, salud del sistema y briefing diario.
- **P1 — Territorio y coaliciones:** datos territoriales válidos, escenarios juntos/separados, sensibilidad, incertidumbre, versiones y explicación.
- **P2 — Inteligencia política ampliada:** instituciones, partidos, candidaturas, programas, declaraciones, cronología territorial.
- **P3 — Validación y mejora continua:** OOS, calibración, latencias, auditoría de alertas, falsos positivos y recuperación.

## 6. Criterios globales de salida

- **Continuidad:** operación sin intervención manual y recuperación de tareas fallidas.
- **Actualidad:** estado de fuentes y demora de detección declarados con métricas reales.
- **Trazabilidad:** reconstrucción de cada alerta y escenario desde datos versionados.
- **Seguridad analítica:** si falta evidencia crítica, no se presenta una conclusión como válida.

## 7. Requisito legal y calendario

El calendario debe obtener fechas y plazos de fuentes oficiales primarias (BOE, INE, JEC, Interior, Congreso/Senado y autoridad competente), guardar el documento fuente y registrar cambios. Toda fecha de convocatoria, campaña, censo, candidaturas, voto o escrutinio debe verificarse contra la publicación oficial vigente. Una fecha escrita en esta especificación es una hipótesis a contrastar, no fuente jurídica suficiente por sí sola.



## Fechas electorales oficiales verificadas para el ciclo 2026

El [Real Decreto 806/2026, BOE-A-2026-20742](https://www.boe.es/buscar/doc.php?id=BOE-A-2026-20742), publicado el 6 de octubre de 2026, convoca elecciones al Congreso y al Senado para el **29 de noviembre de 2026**; fija la campaña del **13 al 27 de noviembre de 2026** y la sesión constitutiva de las Cámaras para el **23 de diciembre de 2026 a las 10:00**. Estas fechas deben materializarse en un calendario versionado con el BOE como evidencia; su verificación documental no demuestra que el calendario operativo exista o esté funcionando.

## 8. Política de auditoría

- Auditar por requisito, no por nombre de módulo.
- No contar existencia de código como prueba de ejecución.
- No contar tests de mocks como prueba de integración real.
- No atribuir cobertura a un requisito sin enlace explícito a evidencia.
- Registrar SHA, fecha, fuente, comando/prueba y resultado.
- No inferir que una capacidad funciona porque un workflow esté configurado.
- No inventar datos, fuentes, métricas, certificaciones o estados PASS.
- Conservar código reutilizable y eliminar solo implementaciones obsoletas o inaplicables después de migrar sus garantías.
