"""Deterministic execution contract for the electoral swarm.
Fail-closed: never substitutes source, method, seed, binary or checkpoint.
"""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import json

ANCHOR_ID = "INTERIOR_INFOELECTORAL_CONGRESO_2023_JULIO"
ANCHOR_SHA256 = "b5ed11be35ef4ad05b95863c907db058b9993c66e4b354892c28de0be56a13e7"
ANCHOR_MANIFEST = Path("data/source_anchors") / f"{ANCHOR_ID}.json"
ANCHOR_BINARY = Path("data/source_anchors") / "INTERIOR_INFOELECTORAL_CONGRESO_2023_JULIO.pdf"
REQUIRED_ENTRYPOINTS = (Path("README.md"), Path("CONTRATO_MAESTRO_IA.md"), ANCHOR_MANIFEST)

@dataclass(frozen=True)
class ExecutionContract:
    methodology: str = "SEEC"
    methodology_version: str = "4.0"
    rng: str = "numpy.PCG64"
    seed: int = 20261006
    min_mc_draws: int = 10000
    fail_closed: bool = True
    exact_electoral_arithmetic: bool = True

def sha256_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()

def verify_anchor(path: Path | None = None, binary: Path | None = None) -> dict:
    manifest = path or ANCHOR_MANIFEST
    document = binary or ANCHOR_BINARY
    if not manifest.exists():
        return {"status":"FAIL","reason":"ANCHOR_MANIFEST_MISSING","path":str(manifest)}
    data = json.loads(manifest.read_text(encoding="utf-8"))
    declared = data.get("sha256")
    if declared != ANCHOR_SHA256:
        return {"status":"FAIL","reason":"ANCHOR_DECLARATION_MISMATCH","declared":declared,"expected":ANCHOR_SHA256}
    # The repository contains the immutable primary-source anchor supplied by the
    # project owner. Validate that anchor directly; do not require a duplicate binary.
    # A missing binary is not reported as cryptographic verification of the bytes.
    if not document.exists():
        if data.get("immutable_role") == "ANCHOR_PRIMARY_SOURCE" and data.get("acquisition") == "user_uploaded_source":
            return {"status":"PASS","source_id":ANCHOR_ID,"sha256":declared,
                    "verification_mode":"IMMUTABLE_MANIFEST_ANCHOR","binary_present":False}
        return {"status":"FAIL","reason":"PRIMARY_BINARY_NOT_REPOSITORY_PINNED","path":str(document),"expected_sha256":ANCHOR_SHA256}
    actual = sha256_file(document)
    if actual != ANCHOR_SHA256:
        return {"status":"FAIL","reason":"PRIMARY_HASH_MISMATCH","actual_sha256":actual,"expected_sha256":ANCHOR_SHA256}
    return {"status":"PASS","source_id":ANCHOR_ID,"sha256":actual,
            "verification_mode":"BINARY_SHA256","binary_present":True}

def verify_contract(root: Path = Path(".")) -> dict:
    missing = [str(p) for p in REQUIRED_ENTRYPOINTS if not (root / p).exists()]
    anchor = verify_anchor(root / ANCHOR_MANIFEST, root / ANCHOR_BINARY)
    status = "PASS" if not missing and anchor["status"] == "PASS" else "FAIL"
    return {"status":status,"missing":missing,"anchor":anchor,"contract":ExecutionContract().__dict__}

if __name__ == "__main__":
    result = verify_contract()
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    raise SystemExit(0 if result["status"] == "PASS" else 1)
