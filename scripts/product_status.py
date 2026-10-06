from __future__ import annotations
from pathlib import Path
import json

def product_status(root="."):
    r=Path(root)
    manifest=json.loads((r/"ci_evidence/historico_manifest.json").read_text(encoding="utf-8"))
    validation=json.loads((r/"ci_evidence/historico_validation.json").read_text(encoding="utf-8"))
    secondary = manifest.get("source_tier")=="SECONDARY_REPLICA" and validation.get("status")=="PASS" and validation.get("source_tier")=="SECONDARY_REPLICA" and validation.get("arithmetic_bad_cells")==0
    if secondary:
        return {
            "status":"OPERATIONAL_BETA",
            "certification":"PARTIAL",
            "use_allowed":True,
            "data_source":"SECONDARY_REPLICA_VERIFIED",
            "evidence":{"manifest_status":manifest.get("source_tier"),"validation_status":validation.get("status"),"arithmetic_bad_cells":validation.get("arithmetic_bad_cells")},
            "warnings":["No es fuente primaria de Interior","No equivale a certificación oficial","No es un predictor electoral validado"]
        }
    return {"status":"BLOCKED","certification":"BLOCKED","use_allowed":False,"data_source":manifest.get("source_tier","UNKNOWN")}

if __name__=="__main__":
    print(json.dumps(product_status(),ensure_ascii=False,indent=2))
