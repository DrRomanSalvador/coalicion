"""Generate the canonical COALICIÓN situation state from repository evidence."""
from __future__ import annotations

from src.situation_state import SituationStateBlocked, write_situation_state

try:
    path = write_situation_state()
except SituationStateBlocked as exc:
    raise SystemExit(str(exc))

print(path)
