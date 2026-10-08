"""Generate the canonical COALICIÓN situation state from repository evidence."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.situation_state import SituationStateBlocked, write_situation_state

try:
    path = write_situation_state()
except SituationStateBlocked as exc:
    raise SystemExit(str(exc))

print(path)
