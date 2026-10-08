# Despliegue de COALICIÓN

## API

La imagen de producción arranca la API por defecto.

Variables obligatorias:
- `COALICION_API_KEY`: clave privada para las rutas de producto.
- `COALICION_API_HOST`: por defecto `127.0.0.1`.
- `COALICION_API_PORT`: por defecto `8080`.

Comprobación:

```bash
curl http://127.0.0.1:8080/healthz
curl -H "X-API-Key: $COALICION_API_KEY" http://127.0.0.1:8080/estado
```

## Docker

```bash
docker build -t coalicion .
docker run --rm -p 8080:8080 -e COALICION_API_KEY="$COALICION_API_KEY" coalicion
```

El contenedor no ejecuta como root y tiene healthcheck.

## Telegram

El bot principal es el único consumidor de `getUpdates`.
Las alertas programadas usan `TELEGRAM_ALLOWED_CHATS`; si está vacío, el sistema falla cerrado.
