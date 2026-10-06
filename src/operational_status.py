"""Operational status: useful beta mode without weakening strict certification."""
from pathlib import Path
import json

def get_status(root="."):
    r=Path(root)
    manifest=r/"ci_evidence/historico_manifest.json"
    data={}
    if manifest.exists():
        try: data=json.loads(manifest.read_text(encoding="utf-8"))
        except Exception: data={}
    tier=data.get("source_tier","UNKNOWN")
    if tier=="PRIMARY_INTERIOR":
        return {"mode":"OPERATIONAL","certification":"STRICT_CANDIDATE","data_source":tier,"use_allowed":True,"warnings":[]}
    if tier=="SECONDARY_REPLICA":
        return {"mode":"OPERATIONAL_BETA","certification":"PARTIAL","data_source":"SECONDARY_REPLICA_VERIFIED","use_allowed":True,
                "warnings":["Datos 2023: réplica secundaria, no fuente primaria","No usar como certificación oficial","No es un predictor validado"]}
    return {"mode":"BLOCKED","certification":"BLOCKED","data_source":tier,"use_allowed":False,"warnings":["No existe una fuente de datos utilizable"]}
