#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOTS = ["data","artifacts","ci_evidence","config","scripts","src","tests"]
OUT = Path("artifacts/sha256_manifest.json")

def sha256(p: Path) -> str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    rows=[]
    for root in ROOTS:
        base=Path(root)
        if not base.exists(): continue
        for p in sorted(x for x in base.rglob("*") if x.is_file()):
            if p == OUT: continue
            rows.append({"path":str(p).replace("\\","/"),"sha256":sha256(p),"size":p.stat().st_size})
    payload={"schema":"ARTIFACT_SHA256_MANIFEST_V1","files":rows,"file_count":len(rows)}
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"file_count":len(rows),"manifest":str(OUT)},ensure_ascii=False))

if __name__=="__main__": main()
