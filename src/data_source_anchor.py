"""Immutable source-anchor verification for SEEC.

The uploaded Interior/Infoelectoral PDF is a canonical evidence object.
This module never downloads or searches for a replacement when the anchor
is present. A hash mismatch is a hard failure.
"""
from __future__ import annotations
from pathlib import Path
import hashlib, json

ANCHOR_SHA256 = "b5ed11be35ef4ad05b95863c907db058b9993c66e4b354892c28de0be56a13e7"
ANCHOR_ID = "INTERIOR_INFOELECTORAL_CONGRESO_2023_JULIO"
MANIFEST = Path("data/source_anchors/INTERIOR_INFOELECTORAL_CONGRESO_2023_JULIO.json")

def verify_bytes(data: bytes) -> bool:
    return hashlib.sha256(data).hexdigest() == ANCHOR_SHA256

def verify_file(path: str | Path) -> dict:
    p=Path(path)
    if not p.exists():
        return {"status":"MISSING","source_id":ANCHOR_ID,"path":str(p)}
    digest=hashlib.sha256(p.read_bytes()).hexdigest()
    return {
        "status":"PASS" if digest == ANCHOR_SHA256 else "FAIL",
        "source_id":ANCHOR_ID,
        "sha256":digest,
        "expected_sha256":ANCHOR_SHA256,
        "path":str(p),
    }

def load_manifest() -> dict:
    if not MANIFEST.exists():
        raise RuntimeError("ANCHOR_MANIFEST_MISSING")
    data=json.loads(MANIFEST.read_text(encoding="utf-8"))
    if data.get("sha256") != ANCHOR_SHA256:
        raise RuntimeError("ANCHOR_MANIFEST_HASH_MISMATCH")
    return data

if __name__=="__main__":
    print(json.dumps(load_manifest(),ensure_ascii=False,indent=2))
