#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
LOG="artifacts/execution_log.md"
mkdir -p artifacts
touch "$LOG"
MAX_ATTEMPTS="${MAX_ATTEMPTS:-5}"
RETRY_DELAY="${RETRY_DELAY:-10}"
for i in $(seq 1 "$MAX_ATTEMPTS"); do
  echo "=== Intento $i/$MAX_ATTEMPTS ==="
  printf '%s\n' "- $(date -u +%Y-%m-%dT%H:%M:%SZ) — ROBUST_RUN intento=$i/$MAX_ATTEMPTS" >> "$LOG"
  if python scripts/ai_electoral_data_engine.py --retry-on-fail; then rc=0; else rc=$?; fi
  if [ -s artifacts/data/election_2023_canonical.json ]; then
    echo "Matriz canónica generada"
    break
  fi
  echo "Motor falló rc=$rc"
  if [ "$i" -lt "$MAX_ATTEMPTS" ]; then sleep "$RETRY_DELAY"; fi
done
if [ ! -s artifacts/data/election_2023_canonical.json ]; then
  echo "Fallback secundario solicitado; no sustituye fuente primaria."
  python scripts/ai_electoral_data_engine.py --fallback-to-secondary --source eleccionesdb --retry-on-fail || true
fi
if [ -s artifacts/data/election_2023_canonical.json ]; then
  python - <<'PY'
import json
from pathlib import Path
m=json.loads(Path("artifacts/data/election_2023_canonical.json").read_text(encoding="utf-8"))
p=m.get("data",{}).get("provinces",[])
print("Provincias:",len(p))
print("Escaños:",sum((x.get("seats") or 0) for x in p))
print("Estado:",m.get("validation",{}).get("status"))
PY
else
  echo "Matriz canónica no generada."
fi
python scripts/product_status.py || true
tail -100 artifacts/execution_log.md || true
exit 0
