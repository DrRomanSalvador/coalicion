# COALICIÓN — CONTRATO MAESTRO DE EJECUCIÓN

**Estado:** NORMAS INVIOLABLES  
**Prioridad:** MÁXIMA  
**Aplicación:** toda IA, agente, script, automatización o colaborador que trabaje en este repositorio.

## 1. Arranque obligatorio
Antes de modificar cualquier elemento se debe leer este contrato y README.md, comprobar la versión de los datos y respetar una única metodología. Si existe una contradicción, se detiene la ejecución y se registra; nunca se resuelve silenciosamente.

## 2. Principio supremo
**Mismos datos + mismas reglas + mismos parámetros + misma versión = mismo resultado.** No se ajustan parámetros para acercarse a un resultado político, encuesta o modelo externo.

## 3. Cadena única
FUENTES → DATOS → VALIDACIÓN → SESGOS → TERRITORIO → ESCENARIO → COALICIÓN → LEY ELECTORAL → MARGINALIDAD → INCERTIDUMBRE → RESULTADO → AUDITORÍA

Cada capa tiene entradas, salidas, reglas, parámetros, pruebas, versión y trazabilidad.

## 4. Evidencia
- **A:** observado en fuente primaria/oficial.
- **B:** reproducido determinísticamente desde A.
- **C:** imputado.
- **D:** supuesto.
- **E:** escenario.

Nunca se presenta B/C/D/E como A. Toda imputación conserva su etiqueta y su incertidumbre.

## 5. Prohibiciones absolutas
Queda prohibido:
- inventar votos territoriales;
- convertir escaños publicados en porcentajes no publicados;
- sumar escaños para simular coaliciones;
- ajustar manualmente escaños o provincias;
- ocultar imputaciones;
- mezclar fechas sin registro;
- usar información futura en validación histórica;
- cambiar de metodología según la fuente;
- redondear antes de una frontera electoral;
- introducir una corrección sin backtesting fuera de muestra;
- seleccionar solo elecciones favorables a una hipótesis;
- presentar incertidumbre como certeza.

## 6. Ley electoral
El Congreso tiene 350 escaños y 52 circunscripciones. Para las elecciones de 29-11-2026 se usan exclusivamente las magnitudes del Real Decreto 806/2026.

En circunscripciones provinciales se aplica el 3% de votos válidos y D'Hondt con cocientes exactos. Los empates de cocientes se resuelven por mayor voto total; si también hay igualdad absoluta, el programa no decide arbitrariamente: devuelve un estado de empate pendiente del mecanismo legal de sorteo/alternancia.

Ceuta y Melilla tienen un diputado cada una y se adjudican al candidato/candidatura con mayor número de votos; no se aplica D'Hondt.

## 7. Territorialización
La cadena es obligatoria:

% nacional → votos territoriales → candidaturas elegibles → ley electoral → escaños

Nunca se invierte escaños → % nacional. Una candidatura sin base territorial comparable no recibe territorialidad inventada. Si la imputación es inevitable, queda explícita como C y aumenta la incertidumbre; si no es defendible, el escenario se declara no reconstruible.

## 8. Coaliciones y fusiones
Los votos de candidaturas fusionadas o coaligadas se combinan por circunscripción antes de aplicar la ley electoral. Nunca se suman escaños.

## 9. Correcciones de encuestas
Una corrección solo entra si una validación temporal rolling/expanding demuestra mejora frente al modelo base sin información futura. Se evalúan como mínimo voto, escaños, partido, territorio, calibración y estabilidad. Si no supera el modelo base, la corrección es cero.

## 10. Marginalidad
Para cada frontera se conserva último cociente ganador, primer cociente perdedor, diferencia, candidatura y votos necesarios para desplazarla. La marginalidad mide sensibilidad; nunca fabrica escaños.

## 11. Incertidumbre
Se separan incertidumbre estadística, territorial, de modelo y política/temporal. Se propaga a escaños cuando los datos permiten hacerlo reproduciblemente.

## 12. Control de cambios
Cada cambio registra qué cambia, por qué, evidencia, pruebas, impacto, versión y hash. No se sobrescriben silenciosamente reglas ni validaciones anteriores.

## 13. Auditoría adversarial
Antes de aceptar un resultado se comprueban 52 circunscripciones, 350 escaños, conservación de votos, umbrales, D'Hondt, empates, Ceuta/Melilla, coaliciones, faltantes, determinismo y reproducibilidad.

## 14. Regla de parada
Ante datos esenciales ausentes, contradicciones, empate absoluto no resuelto, territorialidad no defendible o fallo de reproducibilidad:

DETENER → IDENTIFICAR → REGISTRAR → NO PROPAGAR

## 15. Continuidad
Este contrato es la memoria operativa acumulada del proyecto. Una nueva IA debe poder reconstruir el procedimiento sin disponer de conversaciones anteriores. Toda ampliación debe ser compatible, explícita, versionada y comprobable.


## 16. Registro exhaustivo de sesgos
Antes de diseñar o aceptar una corrección debe consultarse `docs/REGISTRO_MAESTRO_SESGOS.md`. La hipótesis **Gobierno × partido × casa × fecha** debe probarse como interacción candidata, junto con recencia, modo, no respuesta, recuerdo, ocultación, turnout, dependencia/herding, ciclo electoral, fragmentación, nuevos partidos y todos los demás factores registrados. Ninguno se convierte en corrección fija sin evidencia OOS. Los efectos con poco soporte sufren shrinkage y, si no generalizan, se reducen a cero.

## 17. Regla de amplitud sin sobreajuste
La exhaustividad se obtiene registrando y probando todas las fuentes plausibles de error, no incluyendo todas simultáneamente. Los modelos se comparan anidados y fuera de muestra. La complejidad adicional solo sobrevive si mejora la generalización conjunta de voto, territorio, escaños, calibración y estabilidad.