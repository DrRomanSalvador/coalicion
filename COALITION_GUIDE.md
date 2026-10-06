# Guía de coaliciones

## Pregunta
“¿Qué ocurre si A y B concurren juntos?”

COALICIÓN suma los votos de A y B **por circunscripción** y vuelve a ejecutar D'Hondt. Nunca suma los escaños ya obtenidos por separado.

## Interpretación
- `delta > 0`: la coalición obtiene más escaños que las candidaturas separadas bajo los supuestos dados.
- `delta < 0`: obtiene menos.
- `delta = 0`: no cambia la asignación.
- Los cambios se reportan por circunscripción.

## Estado beta
Con datos secundarios, el resultado es `OPERATIONAL_BETA / PARTIAL`. Esto permite análisis de decisión, pero no certificación oficial.

## Supuestos
Cada escenario debe declarar procedencia, territorialización y supuestos. Si faltan, el escenario se rechaza.
