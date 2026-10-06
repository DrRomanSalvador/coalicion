# Pipeline de datos

El programa ya no depende de que el usuario introduzca manualmente las tablas de 2023.

Fuente de descarga por defecto: dataset público del Ministerio del Interior, `Elecciones-Congreso.xlsx`.

Uso:

```bash
python cli.py download
python cli.py inspect
python cli.py normalize
```

El normalizador conserva las etiquetas territoriales y de candidatura tal como aparecen en la fuente. No agrupa partidos por parecido de nombre.

La fuente pública del Ministerio ofrece el dataset del Congreso en XLSX y datos de participación. El motor de predicción utiliza después los datos normalizados como entrada territorial.


## Política de materialización

El pipeline distingue dos clases:

### 1. Datos históricos o versionables
Se descargan y se conservan dentro del repositorio con:
- artefacto original;
- fecha de adquisición;
- tamaño;
- SHA-256;
- URL primaria;
- catálogo oficial;
- transformación reproducible.

Una nueva versión no sobrescribe la trazabilidad anterior: Git conserva el historial del artefacto.

### 2. Datos vivos o susceptibles de actualización
El repositorio conserva el enlace a la fuente primaria y su identificador de catálogo. Cuando se materializa una copia, esta queda asociada a un hash y a la fecha de adquisición. El motor no sustituye una fuente viva por una copia antigua sin marcarla como snapshot.

### Fuentes actualmente automatizadas
- Ministerio del Interior — `Elecciones-Congreso.xlsx`: descarga, hash, inspección y normalización.
- INE — `pobmun.zip`: descarga y hash.
- CIS — catálogo de estudios: índice vivo con fecha y hash de la respuesta adquirida.
- BOE/JEC: índice vivo; los documentos electorales o jurídicos versionados deben fijarse por identificador y fecha.

El workflow canónico es `.github/workflows/materializar_fuentes_oficiales.yml`. Se ejecuta por calendario y manualmente desde GitHub.

**Fail-closed:** si una descarga falla o cambia de esquema, no se debe inventar una equivalencia; se conserva el error y se detiene la transformación dependiente.
