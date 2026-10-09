#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data.collector import write_normalized
result = write_normalized(
    ROOT / "data/surveys/current_2026/current_national.json",
    ROOT / "artifacts/surveys/current_2026_normalized.json",
)
print(result["normalized_hash"])
