# Gobernanza de requisitos de producto COALICIÓN

## Fuente de verdad

La lista canónica exhaustiva de **430 requisitos de producto** es la fuente de verdad para el futuro de COALICIÓN. No se puede sustituir por las funcionalidades que hoy existen, por el contenido de los tests ni por una lista improvisada por el agente. Cada requisito debe contrastarse individualmente con evidencia materializada en el repositorio.

La lista debe conservar los identificadores y la redacción originales. Si la fuente exacta no está disponible, la Colmena queda bloqueada para ejecución de misiones de producto: no se reconstruyen requisitos de memoria ni se declara cobertura ficticia.

## Dominios que deben quedar representados

Estos dominios orientan la reconciliación, pero **no sustituyen** los 430 elementos atómicos:

1. Producto, experiencia de usuario, accesibilidad y flujo de decisión.
2. Datos electorales oficiales e históricos, incluyendo 2004–2023 y procedencia/hash.
3. Encuestas: descubrimiento, ingesta, normalización, historial, salud de fuentes y alertas de publicación/recuperación.
4. Territorialización y base 2026 para las 52 circunscripciones.
5. Proyección, escenarios, backtesting fuera de muestra, calibración e incertidumbre.
6. Reparto D’Hondt, marginalidad, último cociente, primer perdedor y votos necesarios para cambiar escaños.
7. Coaliciones: listas separadas frente a coaligadas, transferencias, fugas, abstención y voto estratégico con supuestos explícitos.
8. Mapas, comparación antes/después y explicación de resultados por territorio.
9. Alertas accionables multicanal y catálogo de los 97 tipos de alerta referidos en la especificación original.
10. Informes, explicación, trazabilidad y exportación.
11. Operación continua, calendario electoral, elecciones súbitas, día electoral y postelectoral.
12. Seguridad, privacidad, permisos, APIs, colaboración y multiempresa.
13. Validación, reproducibilidad, auditoría independiente, certificación y release.
14. Diferenciación comercial y utilidad demostrable para responsables de decisión.

## Circuito operativo prioritario

El producto debe poder recorrer de forma trazable:

**encuesta → voto → territorio → D’Hondt → escaños → marginalidad → pacto → transferencia → escenario → incertidumbre → explicación → alerta.**

El circuito debe operar por circunscripción, indicar fuentes y supuestos, señalar el último cociente/primer perdedor y los votos que cambiarían la asignación cuando los datos lo permitan. La falta de cobertura territorial o de una fuente necesaria debe mostrarse como limitación o bloqueo; nunca se rellena con datos inventados.

## Cómo gobierna la Abeja Reina

- Cada misión atómica referencia uno o más IDs de los 430 requisitos.
- Cada requisito queda enlazado a evidencia, tests, estado, dependencias, riesgos y misión responsable.
- Las 179 misiones son capacidad de coordinación, no 179 objetivos inventados ni prueba de cobertura completa.
- La Reina debe reconciliar el 100 % de los 430 requisitos contra misiones y evidencias antes de declarar completitud.
- Priorizar brechas por utilidad inmediata, impacto de decisión, riesgo, dependencias y tiempo; no por comodidad ni por código ya existente.
- Ejecutar lotes de hasta cinco, con aprobación cuando corresponda, sin solapamientos ni duplicidades.
- Una misión sin requisito fuente, evidencia o criterio de aceptación queda bloqueada.
- Un requisito no implementado no se marca como cubierto porque exista una función de nombre parecido.
- Los principios de ingeniería son controles obligatorios permanentes para todas las misiones, además de los criterios de producto.

## Estado actual de la fuente detallada

La referencia a la lista de 430 requisitos y a los 97 tipos de alerta procede de la especificación maestra previa. Este archivo **no pretende reproducir su contenido exacto**. Hasta materializar la lista original íntegra y verificar 430 IDs únicos, la gobernanza de requisitos permanece **BLOCKED**.
