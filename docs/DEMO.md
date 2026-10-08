# DEMO

La demo actual demuestra comportamiento fail-closed y trazabilidad.

1. Ejecutar la batería de validación.
2. Consultar `/territorio`.
3. Consultar `/evidencia sigma_dos_asturias_20260908`.
4. Ejecutar el pipeline con entrada territorial explícita.

La demo no fabrica un reparto de 350 escaños. Si no existe una matriz provincial explícita para las generales, el pipeline devuelve `BLOCKED_NO_EXPLICIT_TERRITORIAL_INPUT`.
