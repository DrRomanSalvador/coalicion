from __future__ import annotations
from pathlib import Path
import json


def product_status(root="."):
    r = Path(root)
    primary_matrix = r / "artifacts/data/election_2023_canonical.json"
    primary_cert = r / "artifacts/audit/certificate_2023.json"
    primary_validation = r / "artifacts/audit/validation_2023.json"

    if primary_matrix.is_file() and primary_cert.is_file() and primary_validation.is_file():
        matrix = json.loads(primary_matrix.read_text(encoding="utf-8"))
        cert = json.loads(primary_cert.read_text(encoding="utf-8"))
        validation = json.loads(primary_validation.read_text(encoding="utf-8"))
        if (
            matrix.get("source") == "INTERIOR_PRIMARY"
            and cert.get("source_of_truth") == "INTERIOR_PRIMARY"
            and cert.get("province_count") == 52
            and validation.get("status") == "PASS"
        ):
            return {
                "status": "OPERATIONAL_BETA",
                "certification": "PRIMARY_DATA_VALIDATED",
                "use_allowed": True,
                "data_source": "INTERIOR_PRIMARY_SNAPSHOT",
                "evidence": {
                    "province_count": cert.get("province_count"),
                    "validation_status": validation.get("status"),
                    "merkle_root": cert.get("merkle_root"),
                },
                "warnings": [
                    "La validación de datos no equivale a certificación jurídica electoral.",
                    "No implica que la predicción electoral esté validada.",
                ],
            }

    manifest_path = r / "ci_evidence/historico_manifest.json"
    validation_path = r / "ci_evidence/historico_validation.json"
    if manifest_path.is_file() and validation_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        validation = json.loads(validation_path.read_text(encoding="utf-8"))
        secondary = (
            manifest.get("source_tier") == "SECONDARY_REPLICA"
            and validation.get("status") == "PASS"
            and validation.get("source_tier") == "SECONDARY_REPLICA"
            and validation.get("arithmetic_bad_cells") == 0
        )
        if secondary:
            return {
                "status": "OPERATIONAL_BETA",
                "certification": "PARTIAL",
                "use_allowed": True,
                "data_source": "SECONDARY_REPLICA_VERIFIED",
                "evidence": {
                    "manifest_status": manifest.get("source_tier"),
                    "validation_status": validation.get("status"),
                    "arithmetic_bad_cells": validation.get("arithmetic_bad_cells"),
                },
                "warnings": [
                    "No es fuente primaria de Interior.",
                    "No equivale a certificación oficial.",
                    "No es un predictor electoral validado.",
                ],
            }

    return {
        "status": "BLOCKED",
        "certification": "BLOCKED",
        "use_allowed": False,
        "data_source": "PRIMARY_MATRIX_NOT_MATERIALIZED",
    }


if __name__ == "__main__":
    print(json.dumps(product_status(), ensure_ascii=False, indent=2))
