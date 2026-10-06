# REGISTRO MAESTRO DE SESGOS Y CORRECCIONES

## Regla central

Un sesgo documentado no se convierte automáticamente en una corrección. Se distinguen:

1. **Control obligatorio:** elimina una fuente de error de diseño sin aprender una dirección política.
2. **Variable explicativa:** se incorpora al modelo y se estima solo con datos anteriores.
3. **Corrección candidata:** puede alterar la predicción, pero solo entra si gana fuera de muestra.
4. **Incertidumbre:** cuando la evidencia no permite conocer la dirección, se modela como dispersión, no como desplazamiento.
5. **No identificable:** se registra, pero no se fuerza.

La referencia de error es siempre **encuesta − resultado**. Esta convención permite medir signo, MAE, RMSE y error de la distancia entre los dos primeros. El análisis español 2004–2023 muestra que el error común del sector puede dominar el error individual: los grandes fallos de 2004, 2016 y 2023 fueron ampliamente compartidos. Por ello, promediar encuestas no elimina automáticamente el error común. [Fuente metodológica: Polling Forecast, 2026.]

## A. Sesgos de diseño y medición

### A1. No respuesta
Controlar tasa y composición de no respuesta, cuando estén disponibles. No asumir que postestratificar elimina el sesgo. La literatura española identifica la no respuesta como una fuente importante de error.

### A2. Recuerdo de voto
Registrar voto recordado y discrepancia con resultados anteriores. Nunca usar el recuerdo observado como verdad sin modelar ocultación y error de recuerdo.

### A3. Ocultación de voto
Variable candidata, no corrección fija. La evidencia española de 2023 documenta diferencias significativas en recuerdo de PP y Vox asociadas a ocultación y posibles transferencias entre ambos; el efecto debe estimarse fuera de muestra.

### A4. Probabilidad de votar
Separar intención bruta de probabilidad de participación. El ajuste de turnout debe estimarse con información histórica disponible en cada fecha.

### A5. Indecisos / no sabe / no contesta
Registrar denominador, tratamiento y redistribución. No mezclar porcentajes de voto válido con intención bruta.

### A6. Formulación de pregunta y orden
Registrar cuestionario y orden cuando esté disponible. No atribuir un efecto sin evidencia repetida.

### A7. Modo de entrevista
CATI, CAWI, presencial, mixto y panel se registran como variables. El efecto de modo se estima con controles de composición y casa; no se aplica como constante universal.

### A8. Muestreo y ponderación
Registrar marco, cuotas, estratificación, postestratificación, ponderaciones y tamaño efectivo cuando estén disponibles. El n nominal no equivale automáticamente a información efectiva.

## B. Sesgos temporales

### B1. Antigüedad / recencia
La información más reciente puede reflejar mejor el estado actual, pero también más ruido. La ponderación temporal es candidata y se selecciona OOS.

### B2. Movimiento durante el campo
Registrar fecha de inicio y fin. No tratar una encuesta con campo largo como una fotografía instantánea.

### B3. Late swing
La última semana puede contener movimiento electoral que una encuesta anterior no puede observar. Debe separarse de error de muestreo y no corregirse retrospectivamente como si fuera incompetencia de la encuesta.

### B4. Prohibición de publicación
En España existe una ventana legal sin publicación de encuestas. El modelo debe distinguir fecha de campo, fecha de publicación y fecha de elección; no rellenar la ventana con información posterior.

### B5. Eventos extraordinarios
Debates, crisis, decisiones judiciales, pactos, escándalos, cambios de candidatura y otros shocks se registran como eventos fechados. Solo son variables predictivas si existen reglas pre-registradas y suficiente historia OOS.

## C. Sesgos de casa / encuestadora

### C1. House effect
Se estima como desviación de cada casa respecto al consenso contemporáneo, no respecto al resultado, para no contaminar el estimador con el futuro.

### C2. Dependencia entre encuestas
Dos encuestas no son observaciones independientes si comparten panel, metodología, fuente de ponderación o comportamiento de copia/herding. El promedio debe usar pesos efectivos o componentes de varianza común.

### C3. Herding
La convergencia artificial de casas reduce la dispersión aparente sin reducir necesariamente el error común. Debe modelarse como correlación, no como mayor confianza.

### C4. Calidad histórica de la casa
La experiencia pasada solo puede afectar la ponderación mediante un esquema temporal que no use el resultado de la elección que se está prediciendo.

### C5. Transparencia
La disponibilidad de ficha técnica no es precisión. Sirve para calidad de evidencia y para controles de comparabilidad.

## D. Sesgo político/contextual que DEBE probarse, no suponerse

### D1. Partido que gobierna
Registrar en cada elección:
- partido/familia del Gobierno;
- partido/familia en oposición;
- si la casa es pública o privada;
- casa encuestadora;
- modo de entrevista;
- campo;
- muestra;
- voto observado;
- error final.

Debe probarse específicamente la interacción:

**Gobierno × partido × casa × fecha/recencia**

No se presupone que gobernar provoque sobre- o infrarrepresentación. La variable solo sobrevive si mejora predicción OOS.

### D2. Casa × Gobierno
Se puede estimar como interacción únicamente con suficiente soporte histórico. Con pocos casos se aplica shrinkage hacia efectos comunes y finalmente hacia cero.

### D3. Gobierno × ciclo electoral
La etapa del mandato, elecciones anticipadas y proximidad a la convocatoria pueden ser variables de contexto. No se confunden con incumbency causal.

### D4. Incumbencia
Registrar quién gobierna, pero no convertirlo en una penalización o prima fija.

### D5. Familia ideológica / bloque
Puede servir para controlar correlaciones de transferencia, pero no para imponer movimientos simétricos o compensaciones sin evidencia.

## E. Dinámica partidista

### E1. Partidos nuevos
No usar una media histórica inexistente. Separar nacimiento, crecimiento y maduración.

### E2. Partido que cambia de marca / coalición
Crear identidad histórica mediante una tabla explícita de continuidad. Nunca mezclar automáticamente marcas.

### E3. Fragmentación / concentración
Registrar número efectivo de candidaturas y concentración del voto. Puede afectar la conversión a escaños aunque el error de voto nacional sea pequeño.

### E4. Transferencias entre partidos
Modelarlas como composiciones/flujo solo si hay datos compatibles. No deducir transferencias de una única encuesta.

### E5. Abstención diferencial
Separar intención de voto y participación. La conversión debe calibrarse con elecciones anteriores.

## F. Agregación de encuestas

### F1. Media/mediana
Comparar media, mediana y agregadores robustos.

### F2. Ponderación por muestra
La muestra puede aumentar precisión, pero n no corrige sesgo sistemático. Se compara con pesos de varianza efectiva.

### F3. Ponderación por recencia
Se estima mediante OOS.

### F4. Ponderación por casa
Se estima mediante OOS y shrinkage; nunca mediante una clasificación retrospectiva aplicada hacia atrás.

### F5. Correlación
El error común se modela explícitamente; el número de encuestas no puede crear falsa precisión.

### F6. Outliers
Winsorización o exclusión solo mediante regla predefinida. Nunca retirar una encuesta porque contradiga el resultado esperado.

## G. Conversión voto → escaños

### G1. Territorialización
Es el mayor cuello de botella del modelo. Nunca se inventa una matriz provincial.

### G2. D'Hondt
La no linealidad hace que un pequeño error de voto pueda producir varios escaños y que el mismo error nacional tenga efectos distintos según la distribución territorial.

### G3. Umbral del 3%
Se evalúa por circunscripción con votos válidos reales/proyectados, sin redondeo prematuro.

### G4. Marginalidad
Se conserva el cociente ganador/perdedor y la distancia electoral en cada circunscripción.

### G5. Ceuta/Melilla
Tratamiento independiente por mayoría.

## H. Errores de implementación

- fuga de información;
- look-ahead;
- supervivencia de casas;
- selección de la última encuesta;
- mezcla de fechas;
- redondeo;
- denominadores incompatibles;
- duplicación de encuestas;
- cambios silenciosos de etiqueta partidista;
- datos secundarios sustituyendo primarios;
- inversión escaños→voto;
- ajuste manual territorial;
- suma de escaños de coaliciones;
- empate absoluto resuelto arbitrariamente.

Todos son **bloqueantes**, no variables estadísticas.

## I. Principio específico sobre “quién gobierna × quién encuesta”

El proyecto incorporará esta hipótesis como una familia de modelos anidados:

M0 = base temporal/agregada  
M1 = M0 + house effects  
M2 = M1 + gobierno/incumbencia  
M3 = M2 + gobierno×house  
M4 = M3 + recencia/field_end  
M5 = M4 + modo/muestra/no-respuesta cuando existan  
M6 = M5 + interacciones partidistas/transferencias con soporte

Cada modelo se evalúa con exactamente las mismas ventanas OOS. Se aplica shrinkage jerárquico cuando el número de observaciones es pequeño.

**Nunca se elige M6 por ser más sofisticado. Se elige el modelo que generaliza mejor.**

## J. Métricas obligatorias

Separar:

- MAE y RMSE de voto por partido;
- error firmado por partido;
- error de la distancia entre los dos primeros;
- MAE/RMSE de escaños;
- error territorial;
- calibración de intervalos;
- cobertura;
- estabilidad entre ventanas;
- sensibilidad a ponderaciones;
- rendimiento en elecciones extraordinarias.

Una corrección que mejora voto pero empeora escaños no domina. Una corrección que mejora una elección y empeora sistemáticamente las restantes no domina.

## K. Correcciones que actualmente NO deben fijarse

No se fija de antemano:
- “PSOE +X”;
- “PP −X”;
- “la casa Y siempre hace Z”;
- “si gobierna X hay que subir/bajar Y”;
- una corrección uniforme de 2023;
- una corrección permanente de última semana;
- una prima/penalización de una familia política.

La evidencia histórica española disponible muestra que los signos cambian entre elecciones; por ejemplo, el PSOE pasó de errores negativos a positivos y volvió a negativos, y el PP alternó ambos signos. Por tanto, el historial sirve para estimar incertidumbre y probar modelos, no para imponer una dirección política permanente.

## L. Criterio definitivo

Una corrección entra en producción únicamente si:

**sin información futura + suficiente soporte + especificación predefinida + backtesting temporal + mejora conjunta voto/escaños + no deterioro de calibración/estabilidad + reproducibilidad.**

En caso contrario:

**CORRECCIÓN = 0.**

Fuentes metodológicas principales:
- Polling Forecast, “Medir el error de las encuestas españolas, 2004–2023” (2026).
- Polling Forecast, “Hacia dónde se inclina cada encuestadora” (house effects).
- Delicado & Udina, REIS: evaluación de sondeos y sesgo en conversión a escaños.
- Pavía & Larraz, REIS: no respuesta y modelos de superpoblación.
- Alaminos & Alaminos-Fernández, REIS: recuerdo de voto, ocultación y transferencias tras 2023.
- LOREG art. 69: requisitos técnicos y transparencia de encuestas.


## D8. Contexto de gobierno y movimiento electoral

Desde 2004, cada observación histórica debe conservar, cuando esté documentado:
- quién gobernaba;
- si el partido analizado era gobierno, oposición o socio;
- si hubo cambio de gobierno antes de la elección;
- error con signo y magnitud;
- cambio real del partido frente a la elección anterior;
- cambio que sugería la encuesta;
- diferencia entre ambos cambios.

La métrica clave no será únicamente **encuesta − resultado**. Se analizará también:

**cambio real = resultado_t − resultado_t-1**

**cambio observado = encuesta_t − resultado_t-1**

**error de cambio = cambio observado − cambio real**

Así se separa un nivel sistemáticamente mal estimado de una incapacidad para detectar el movimiento entre elecciones.

No se atribuirá un efecto al gobierno solo porque coincida con un error. La variable gobierno compite con casa, partido, fecha de campo, método, elección y otros controles dentro de validación temporal.
