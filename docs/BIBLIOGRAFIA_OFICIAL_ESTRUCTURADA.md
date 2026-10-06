# Bibliografía oficial estructurada — REINA-SEEC

**Proyecto:** REINA-SEEC  
**Repositorio:** `DrRomanSalvador/coalicion`  
**Metodología:** SEEC 4.0  
**Estado de integración:** REGISTRO ESTRUCTURADO  
**Regla:** las fuentes primarias prevalecen sobre las secundarias; ninguna fuente secundaria puede certificar por sí sola un dato electoral.

## 1. Registro maestro de fuentes

| ID | Fuente | Clase | Uso |
|---|---|---|---|
| ELEC-INT-INFO | Ministerio del Interior — Infoelectoral | PRIMARY | Resultados electorales oficiales |
| ELEC-INT-DL | Ministerio del Interior — Área de descargas | PRIMARY | Ficheros y matrices oficiales |
| ELEC-DATOSGOB | datos.gob.es — Resultados Electorales | PRIMARY/CATALOG | Descubrimiento y distribución de datos oficiales |
| ELEC-JEC | Junta Electoral Central | PRIMARY | Resultados, actas, proclamaciones y documentación electoral |
| ELEC-BOE-23J | BOE-A-2023-18907 | PRIMARY/LEGAL | 23J 2023 |
| ELEC-BOE-10N | BOE-A-2019-17344 | PRIMARY/LEGAL | 10N 2019 |
| ELEC-BOE-28M | BOE-A-2023-22387 | PRIMARY/LEGAL | 28M 2023 |
| ELEC-BOE-2024-13092 | BOE-A-2024-13092 | PRIMARY/LEGAL | Documentación electoral complementaria |
| ELEC-INT-PUB | Interior — Elecciones y partidos políticos | PRIMARY | Publicaciones y documentación oficial |
| ELEC-DATOSGOB-GEN | datos.gob.es — elecciones generales legislativas | PRIMARY/CATALOG | Series y resultados agregados |
| LEG-LOREG | LOREG consolidada | LEGAL/PRIMARY | Marco jurídico electoral |
| LEG-BOE | BOE | LEGAL/PRIMARY | Legislación y disposiciones oficiales |
| POL-CIS | Centro de Investigaciones Sociológicas | PRIMARY | Encuestas y estudios de opinión |
| POL-CIS-FLASH-2023 | CIS — Encuesta Flash elecciones generales 2023 | PRIMARY | Referencia metodológica y electoral |
| POL-DATOSGOB | datos.gob.es — sondeos electorales | PRIMARY/CATALOG | Catálogo de sondeos públicos |
| DEM-INEBASE | INEbase | PRIMARY | Población y estructura territorial |
| DEM-INE | Instituto Nacional de Estadística | PRIMARY | Estadística oficial |
| DEM-INE-MICRO | INE — microdatos/open data | PRIMARY | Microdatos y explotación territorial |
| INST-CONGRESO | Congreso de los Diputados | PRIMARY | Composición, actividad y contexto parlamentario |
| INST-SENADO | Senado | PRIMARY | Composición, actividad y contexto institucional |
| AUX-RTVE | RTVE — resultados históricos | SECONDARY/AUXILIARY | Contraste y navegación histórica; no sustituye Interior/JEC/BOE |
| AUX-GENCAT | Generalitat de Catalunya — portal electoral | PRIMARY TERRITORIAL | Resultados electorales territoriales |
| SEC-LASEXTA-2026 | LaSexta — encuestas 2026 | SECONDARY/MEDIA | Descubrimiento y contraste; nunca fuente primaria de certificación |

## 2. URLs canónicas

### Resultados electorales oficiales
- https://infoelectoral.interior.gob.es/
- https://infoelectoral.interior.gob.es/es/elecciones-celebradas/area-de-descargas/
- https://datos.gob.es/es/catalogo/e00003801-resultados-electorales
- https://www.juntaelectoralcentral.es/
- https://www.boe.es/diario_boe/txt.php?id=BOE-A-2023-18907
- https://www.boe.es/buscar/doc.php?id=BOE-A-2019-17344
- https://www.boe.es/buscar/doc.php?id=BOE-A-2023-22387
- https://www.boe.es/buscar/doc.php?id=BOE-A-2024-13092
- https://www.interior.gob.es/opencms/gl/archivos-y-documentacion/documentacion-y-publicaciones/publicaciones/publicaciones-descargables/elecciones-y-partidos-politicos/
- https://datos.gob.es/ca/catalogo/a14002961-elecciones-generales-legislativas-congreso-principales-resultados

### Marco legal
- https://www.boe.es/buscar/act.php?id=BOE-A-1985-8946
- https://www.boe.es/

### Encuestas y opinión
- https://www.cis.es/
- https://www.cis.es/es/estudios/encuesta-flash-elecciones-generales-2023
- https://datos.gob.es/es/catalogo/conjuntos-datos?tags_es=Sondeos+electorales
- https://www.lasexta.com/elecciones/generales/encuestas-elecciones-generales_202610056ac365161c30184d44b52907.html

### Demografía y territorio
- https://www.ine.es/dyngs/INEbase/es/categoria.htm?c=Estadistica_P&cid=1254734710984
- https://www.ine.es/
- https://ine.es/ss/Satellite?L=es_ES&c=Page&cid=1259942408928&p=1259942408928&pagename=ProductosYServicios/PYSLayout

### Parlamento e instituciones
- https://www.congreso.es/
- https://www.senado.es/

### Fuentes territoriales y auxiliares
- https://resultados-elecciones.rtve.es/
- https://eleccions.gencat.cat/

## 3. Jerarquía de evidencia

1. **PRIMARY:** Interior, JEC, BOE, CIS, INE y portales electorales oficiales competentes.
2. **LEGAL:** BOE y normativa electoral vigente; prevalece para reglas, magnitudes y fechas jurídicas.
3. **METHODOLOGICAL:** documentación técnica, microdatos y metadatos de los organismos oficiales.
4. **SECONDARY:** medios y agregadores; sirven para descubrimiento, contraste o cobertura, nunca para sustituir el registro oficial.
5. **AUXILIARY:** fuentes útiles para contexto o validación cruzada.

Cuando dos fuentes discrepen, se conserva la discrepancia y se resuelve por autoridad, fecha y ámbito; no se promedia ni se oculta.

## 4. Trazabilidad obligatoria de cada dato

Todo dato incorporado al motor debe conservar, cuando exista:

- `source_id`
- `source_url`
- organismo emisor
- tipo de fuente
- fecha de publicación
- fecha de consulta/extracción
- fecha de campo, si es encuesta
- versión o edición
- identificador del documento/estudio/encuesta
- `sha256` del artefacto descargado cuando sea materializable
- transformación aplicada
- unidad territorial
- ámbito electoral
- nivel de evidencia
- estado de validación
- observaciones/incidencias

## 5. Reglas específicas para encuestas

Cada encuesta debe conservar, si está disponible:

- casa/encuestadora;
- identificador único;
- fecha de publicación;
- inicio y fin de campo;
- muestra;
- método de recogida;
- población objetivo;
- pregunta exacta;
- voto directo;
- estimación publicada;
- indecisos/no sabe/no contesta;
- estimación de escaños;
- ficha técnica;
- fuente original;
- dependencia o panel compartido conocida;
- cambios metodológicos;
- cualquier corrección posterior.

**Prohibición:** no inferir una ficha técnica ausente ni convertir una cifra mediática en dato primario.

## 6. Integración con el motor

Esta bibliografía es el registro de procedencia del motor, no una sustitución de los datos pendientes.

Debe alimentar especialmente:

- matriz oficial candidato/partido × circunscripción × elección;
- resultados históricos comparables;
- archivo histórico de encuestas;
- archivo 2026;
- magnitudes electorales y marco legal;
- territorialización reproducible;
- variables demográficas;
- contexto parlamentario e institucional;
- validación cruzada y control de calidad.

## 7. Estado de evidencia

La existencia de una fuente en este registro **no significa que su contenido ya esté materializado en `data/` ni integrado en el pipeline**.

El proyecto mantiene `AUDITADO CON LIMITACIONES` hasta completar la materialización, hash, validación y conexión reproducible de los datos esenciales.

## 8. Regla de no-futuro

Ningún dato posterior al instante de predicción puede entrar en una reconstrucción histórica, backtest o evaluación OOS. Toda observación debe llevar una marca temporal suficiente para impedir fuga de información.

## 9. Criterio de parada

Si una fuente esencial no está disponible, es ambigua, no reproducible o contradice otra fuente de mayor autoridad, el motor debe conservar el estado de incertidumbre y fallar cerrado (`fail_closed=true`) en lugar de fabricar un valor.

## 10. Alcance

Este registro consolida la bibliografía suministrada para REINA-SEEC y queda como índice canónico de procedencia. Las fuentes secundarias se conservan expresamente para no perder cobertura, pero permanecen subordinadas a las fuentes primarias.
