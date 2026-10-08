#!/usr/bin/env python3
from pathlib import Path

from src.data.collector import write_normalized

ROOT = Path(__file__).resolve().parents[1]
result = write_normalized(
    ROOT / "data/surveys/current_2026/current_national.json",
    ROOT / "artifacts/surveys/current_2026_normalized.json",
)
print(result["normalized_hash"])
