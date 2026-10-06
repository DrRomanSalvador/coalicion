# COALICIÓN — PROTOCOLO OPERATIVO UNIVERSAL

## 0. PROPÓSITO

Este repositorio define un **sistema metodológico**, no una predicción concreta.

Cualquier IA, analista, agente o programa que entre en el proyecto debe poder ejecutar el mismo proceso sobre nuevos datos sin cambiar las reglas.

**Objetivo:** producir estimaciones electorales territorialmente coherentes, matemáticamente exactas, auditables y reproducibles, mejorando solo aquello cuya mejora pueda demostrarse frente al modelo base mediante validación fuera de muestra.

---

## 1. REGLA SUPREMA

> **Mismos datos + mismas reglas + mismos parámetros + misma versión = mismo resultado.**

Cambiar los datos **no** autoriza a cambiar la metodología.

Una mejora metodológica solo puede incorporarse cuando:
1. está definida formalmente;
2. es reproducible;
3. puede aislarse;
4. supera una prueba previamente definida;
5. mejora fuera de muestra;
6. no introduce información retrospectiva;
7. queda documentada y versionada.

---

## 2. CONTRATO PARA TODA IA QUE ENTRE

Toda IA que participe debe:

- leer este README antes de modificar nada;
- respetar la metodología vigente;
- distinguir dato, supuesto, imputación, transformación y resultado;
- no inventar datos ausentes;
- no adaptar una regla para obtener un resultado deseado;
- no copiar resultados de otros modelos para aproximarse a ellos;
- no modificar simultáneamente varias capas del modelo;
- conservar la trazabilidad de cada cálculo;
- comprobar las salidas antes de comunicarlas;
- detener la propagación de cualquier dato o regla que no haya sido validado;
- informar internamente de discrepancias al sistema coordinador, no crear una metodología paralela.

**Ninguna IA tiene autoridad para cambiar por sí sola el contrato metodológico.**

---

## 3. ARQUITECTURA DEL SISTEMA

El sistema se divide en capas independientes:

**FUENTES → DATOS → VALIDACIÓN → SESGOS → TERRITORIO → ESCENARIO → COALICIÓN → LEY ELECTORAL → MARGINALIDAD → INCERTIDUMBRE → RESULTADO → AUDITORÍA**

Una capa no puede modificar silenciosamente otra.

Cada capa debe tener:
- entrada definida;
- salida definida;
- fórmula o regla;
- parámetros;
- pruebas;
- versión;
- registro de cambios.

---

## 4. JERARQUÍA DE EVIDENCIA

Cada dato debe clasificarse como:

**A. Observado:** publicado por una fuente primaria o resultado oficial.

**B. Reproducido:** obtenido mediante cálculo determinista a partir de datos observados.

**C. Imputado:** necesario para completar el modelo pero no observado directamente.

**D. Supuesto:** hipótesis metodológica explícita.

**E. Escenario:** condición hipotética solicitada o analizada.

Nunca se puede presentar B, C, D o E como A.

Cuando existan varias fuentes, se conserva la fuente original y se registra la resolución de discrepancias.

---

## 5. PRINCIPIO DE AISLAMIENTO

Nunca se corrigen simultáneamente varios problemas.

Para estudiar un sesgo:

**MODELO BASE → UNA SOLA MODIFICACIÓN → TEST → COMPARACIÓN**

Si mejora, se congela.

Después se estudia el siguiente sesgo.

Esto permite atribuir cualquier mejora o empeoramiento a una única causa.

---

## 6. SESGOS

Cada sesgo debe tener un expediente independiente:

1. definición;
2. mecanismo causal;
3. evidencia histórica;
4. variable observable;
5. estimador;
6. fórmula;
7. datos de entrenamiento;
8. datos de validación;
9. modelo base;
10. modelo corregido;
11. métrica;
12. resultado;
13. decisión;
14. limitaciones.

Los sesgos potenciales incluyen, entre otros:

- no respuesta;
- cobertura;
- composición muestral;
- modo de entrevista;
- ocultación;
- recuerdo de voto;
- temporalidad;
- transferencias entre partidos;
- voto estratégico;
- entrada/salida de candidaturas;
- discontinuidad territorial;
- traducción voto-escaños;
- marginalidad D'Hondt;
- efecto coalición;
- sobreajuste.

**Existir en la literatura no demuestra que deba aplicarse una corrección.**

---

## 7. BACKTESTING

Toda corrección debe competir contra un modelo base.

La evaluación debe ser temporalmente correcta:

**entrenamiento → validación histórica posterior**

Nunca se utilizan datos futuros para construir una corrección que después se presenta como validada.

Cuando haya suficientes elecciones, se utilizará validación rolling/expanding.

Las métricas se fijan antes de mirar el resultado.

Como mínimo:

- error absoluto de voto;
- error cuadrático de voto;
- error absoluto de escaños;
- error por partido;
- error territorial;
- estabilidad de la corrección;
- calibración de incertidumbre cuando exista.

Una corrección que mejora una elección pero empeora sistemáticamente el conjunto histórico no se incorpora.

---

## 8. TERRITORIALIZACIÓN

Nunca se convierte directamente un porcentaje nacional en escaños.

La cadena obligatoria es:

**porcentaje nacional → votos territoriales → candidaturas elegibles → ley electoral → escaños.**

La transformación territorial debe utilizar una regla única y explícita.

Si se utiliza estabilidad histórica:

[
f_p = rac{P_{p,	ext{encuesta}}}{P_{p,	ext{base}}}
]

y:

[
V_{p,c}^{*}=V_{p,c}^{base}	imes f_p
]

debe documentarse qué ocurre cuando no existe base comparable.

No se permite crear territorialidad artificial para favorecer una candidatura.

---

## 9. PARTIDOS SIN BASE HISTÓRICA

Una candidatura nueva no puede recibir una distribución territorial inventada y presentarla como observación.

Debe clasificarse explícitamente como:

**sin base comparable → imputación necesaria → método de imputación → incertidumbre.**

Si no puede identificarse razonablemente su distribución territorial, el modelo debe reconocer esa limitación.

---

## 10. COALICIONES

Las coaliciones se modelan sobre votos territoriales.

Nunca:

**escaños A + escaños B = escaños coalición.**

Siempre:

**votos A por circunscripción + votos B por circunscripción → candidatura conjunta → ley electoral.**

La ventaja o pérdida electoral de una coalición debe surgir únicamente de:
- suma territorial;
- umbral;
- concentración geográfica;
- cocientes electorales;
- reglas legales.

No existe una «prima de coalición» añadida manualmente.

---

## 11. MARGINALIDAD ELECTORAL

El sistema debe calcular para cada circunscripción:

- último cociente ganador;
- primer cociente perdedor;
- partido que gana;
- partido que pierde;
- diferencia absoluta;
- diferencia relativa;
- votos necesarios para alterar el escaño.

La marginalidad sirve para **medir sensibilidad**, no para añadir escaños artificialmente.

Los votos de una coalición afectan de forma diferente a cada circunscripción porque los cocientes D'Hondt son territoriales.

---

## 12. LEY ELECTORAL

La implementación debe reproducir literalmente la legislación vigente.

Para España:

- circunscripciones oficiales;
- número de escaños;
- umbral aplicable;
- D'Hondt;
- desempates legales;
- reglas especiales de Ceuta y Melilla;
- orden de candidatura cuando corresponda.

No se sustituye una regla legal por una aproximación matemática equivalente solo si esa equivalencia no ha sido demostrada.

---

## 13. PRECISIÓN NUMÉRICA

Cuando una diferencia pueda cambiar un escaño:

- utilizar aritmética exacta o racional;
- evitar redondeos intermedios;
- conservar precisión completa;
- redondear únicamente para presentación.

Nunca se decide una frontera electoral sobre porcentajes previamente redondeados.

---

## 14. INCERTIDUMBRE

Debe distinguirse:

**error estadístico ≠ incertidumbre territorial ≠ incertidumbre de modelo ≠ incertidumbre política/temporal.**

Una cifra puntual no debe aparentar una precisión que los datos no permiten.

Cuando sea posible, la incertidumbre se propagará desde votos hasta escaños mediante simulación reproducible.

---

## 15. COMPARACIÓN CON OTROS ANALISTAS

Los resultados externos se utilizan como **referencia de contraste**, nunca como objetivo.

Para cada modelo externo se separará:

- dato publicado;
- metodología conocida;
- resultado publicado;
- diferencia frente a nuestro modelo;
- posible causa matemática;
- evidencia disponible.

Nunca se modifica nuestro modelo para acercarlo a otro resultado sin evidencia independiente.

No se reconstruyen porcentajes a partir de escaños cuando la fuente no los publica.

---

## 16. AUDITORÍA ADVERSARIAL

Cada resultado debe intentar ser refutado antes de aceptarse.

Controles mínimos:

- suma de votos;
- suma de escaños;
- número de circunscripciones;
- magnitudes territoriales;
- umbrales;
- desempates;
- fronteras marginales;
- conservación de datos;
- ausencia de doble conteo;
- ausencia de redondeo peligroso;
- reproducibilidad desde cero.

Un resultado no auditado es un resultado provisional.

---

## 17. CONTROL DE CAMBIOS

Toda modificación metodológica debe registrar:

**qué cambia → por qué → evidencia → fórmula → pruebas → impacto → versión.**

Los datos pueden actualizarse sin cambiar la metodología.

La metodología solo cambia mediante una modificación explícita y versionada.

Nunca se sobrescribe silenciosamente una regla anterior.

---

## 18. REPRODUCCIÓN INDEPENDIENTE

Todo resultado final debe poder ser reconstruido por una segunda implementación independiente utilizando:

- mismos datos;
- mismos parámetros;
- mismas reglas;
- misma versión metodológica.

Si dos implementaciones legítimas producen resultados distintos, el resultado no se considera cerrado hasta encontrar la causa.

---

## 19. PROHIBICIONES ABSOLUTAS

Está prohibido:

- ajustar manualmente escaños;
- ajustar provincias a posteriori;
- modificar parámetros para coincidir con una encuesta;
- sumar escaños para simular coaliciones;
- inferir porcentajes no publicados a partir de escaños;
- inventar datos territoriales;
- ocultar imputaciones;
- mezclar datos de distintas fechas sin registrarlo;
- cambiar la metodología entre fuentes;
- utilizar información futura en una validación histórica;
- seleccionar solo las elecciones que favorecen una corrección;
- introducir una corrección sin prueba;
- redondear antes de una frontera electoral;
- presentar incertidumbre como certeza.

---

## 20. CRITERIO FINAL DE ACEPTACIÓN

Un modelo solo se considera **válido** cuando:

1. sus datos son trazables;
2. sus reglas son explícitas;
3. sus cálculos son reproducibles;
4. sus resultados son replicables;
5. sus transformaciones son reutilizables;
6. sus correcciones superan backtesting;
7. sus límites están declarados;
8. su implementación reproduce la ley electoral;
9. una auditoría independiente puede reconstruirlo;
10. no contiene ajustes orientados al resultado.

### REGLA FINAL

> **La metodología manda sobre el resultado.**
>
> **Los datos pueden cambiar.**
>
> **Los resultados pueden cambiar.**
>
> **Las reglas no cambian para obtener un resultado.**
>
> **Solo cambia una regla cuando la evidencia demuestra que la regla anterior era inferior.**
