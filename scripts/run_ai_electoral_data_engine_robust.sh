#!/usr/bin/env bash
# Alias de compatibilidad para el runner canónico.
exec "$(cd "$(dirname "$0")" && pwd)/run_ai_electoral_engine_robust.sh" "$@"
