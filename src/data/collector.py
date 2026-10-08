"""Fail-closed normalizer for current survey registry data.

This module deliberately separates acquisition from normalization. It does not
silently scrape or invent missing field dates, samples, methodology, or URLs.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


REQUIRED = ("id", "pollster", "publication_date", "shares", "evidence_level", "source_url")
PARTIES = ("PP", "PSOE", "Vox", "Sumar")


def _hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def normalize_registry(source: Path, *, official: bool = False) -> dict[str, Any]:
    data = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("surveys"), list):
        raise ValueError("BLOCKED: invalid survey registry")

    rows = []
    for raw in data["surveys"]:
        if not isinstance(raw, dict) or any(not raw.get(k) for k in REQUIRED):
            raise ValueError("BLOCKED: survey missing required provenance")
        shares = raw["shares"]
        if not isinstance(shares, dict) or any(p not in shares for p in PARTIES):
            raise ValueError("BLOCKED: incomplete party share vector")
        if official and raw.get("evidence_level") != "PRIMARY_VERIFIED":
            raise ValueError("BLOCKED: official mode requires PRIMARY_VERIFIED evidence")
        rows.append({
            "id": str(raw["id"]),
            "pollster": str(raw["pollster"]),
            "publication_date": str(raw["publication_date"]),
            "field_start": raw.get("field_start"),
            "field_end": raw.get("field_end"),
            "sample_size": raw.get("sample_size"),
            "methodology": raw.get("methodology"),
            "shares": {p: float(shares[p]) for p in PARTIES},
            "evidence_level": str(raw["evidence_level"]),
            "source_url": str(raw["source_url"]),
        })

    return {
        "schema": "NORMALIZED_CURRENT_SURVEYS_V1",
        "as_of": data.get("as_of"),
        "count": len(rows),
        "surveys": rows,
        "source_registry_hash": _hash(data),
        "normalized_hash": _hash(rows),
        "official": official,
        "fail_closed": True,
    }


def write_normalized(source: Path, output: Path, *, official: bool = False) -> dict[str, Any]:
    result = normalize_registry(source, official=official)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result
