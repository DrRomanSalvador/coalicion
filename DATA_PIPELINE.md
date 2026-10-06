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
