"""Deterministic hashes for Phase 2 release evidence."""
from __future__ import annotations
import hashlib, json, platform, sys
from pathlib import Path
from typing import Any

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def sha256_json(value: Any) -> str:
    return sha256_bytes(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))

def file_sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())

def environment_fingerprint() -> dict[str, str]:
    return {"python": sys.version.split()[0], "implementation": platform.python_implementation(), "platform": platform.platform()}

def reproducibility_record(*, input_value: Any, output_value: Any, code_files: list[Path]) -> dict[str, Any]:
    return {
        "schema":"REPRODUCIBILITY_RECORD_V1",
        "input_sha256":sha256_json(input_value),
        "output_sha256":sha256_json(output_value),
        "code_sha256":sha256_json({str(p):file_sha256(p) for p in sorted(code_files, key=str)}),
        "environment":environment_fingerprint(),
        "fail_closed":True,
    }
