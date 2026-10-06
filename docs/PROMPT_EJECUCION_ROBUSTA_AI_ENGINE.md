# PROMPT DE EJECUCIÓN ROBUSTA — AI ELECTORAL DATA ENGINE

Ejecutar en `DrRomanSalvador/coalicion`:

```bash
MAX_ATTEMPTS=5 RETRY_DELAY=10 bash scripts/run_ai_electoral_engine_robust.sh
```

Reglas obligatorias:
- máximo 5 reintentos del motor;
- registrar cada fallo y cada SHA-256 obtenido;
- tolerar HTTP, URL, timeout y errores transitorios;
- mantener verificación TLS; nunca usar `--insecure`;
- Interior es la única fuente de verdad para votos oficiales;
- INE/CIS son auxiliares y no se promedian con votos;
- cualquier réplica secundaria se conserva como evidencia secundaria y nunca se etiqueta como oficial;
- no inventar escaños, provincias, votos ni partidos;
- si faltan datos críticos, mantener `PARTIAL/BLOCKED`;
- generar certificado y Merkle root solo sobre datos realmente materializados;
- verificar al final matriz, certificado, reconciliación y log.

Criterio primario: matriz canónica de Interior + validación PASS + 52 circunscripciones verificadas + artefactos criptográficos.

Si Interior no está disponible, el resultado secundario debe quedar explícitamente marcado como `SECONDARY_REPLICA`; no puede reemplazar silenciosamente la matriz primaria.
