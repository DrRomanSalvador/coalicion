#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, ssl, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"
LOG = ART / "exhaustive_search_2023.json"
RAW = ROOT / "data" / "raw" / "exhaustive"

SOURCES = [
    {"id":"INTERIOR_CONGRESO_XLSX","tier":"PRIMARY","authority":"MINISTERIO_INTERIOR","urls":["https://descargas.interior.gob.es/datasets/resultados_electorales/Elecciones-Congreso.xlsx"],"format":"xlsx","role":"official_vote_matrix"},
    {"id":"INTERIOR_CARGOS_ELECTOS_XLSX","tier":"PRIMARY","authority":"MINISTERIO_INTERIOR","urls":["https://descargas.interior.gob.es/datasets/resultados_electorales/Elecciones-Congreso-cargos-electos.xlsx"],"format":"xlsx","role":"elected_members"},
    {"id":"BOE_JEC_2023_RESULTS","tier":"PRIMARY","authority":"JUNTA_ELECTORAL_CENTRAL","urls":["https://www.boe.es/buscar/doc.php?id=BOE-A-2023-18907","https://www.boe.es/boe/dias/2023/09/01/pdfs/BOE-A-2023-18907.pdf"],"format":"html_or_pdf","role":"official_results_and_seats"},
    {"id":"BOE_JEC_2023_CORRECTION","tier":"PRIMARY","authority":"JUNTA_ELECTORAL_CENTRAL","urls":["https://www.boe.es/buscar/doc.php?id=BOE-A-2023-19537"],"format":"html","role":"official_correction"},
    {"id":"DATOS_GOB_INTERIOR_CATALOG","tier":"PRIMARY","authority":"MINISTERIO_INTERIOR","urls":["https://datos.gob.es/es/catalogo/e00003801-resultados-electorales","https://datos.gob.es/ca/catalogo/a14002961-elecciones-generales-legislativas-congreso-principales-resultados"],"format":"html","role":"official_catalog_provenance"},
    {"id":"INTERIOR_DOWNLOADS_CATALOG","tier":"PRIMARY","authority":"MINISTERIO_INTERIOR","urls":["https://infoelectoral.interior.gob.es/es/elecciones-celebradas/area-de-descargas/"],"format":"html","role":"official_download_catalog"},
    {"id":"JEC_OFFICIAL","tier":"PRIMARY","authority":"JUNTA_ELECTORAL_CENTRAL","urls":["https://www.juntaelectoralcentral.es/"],"format":"html","role":"official_legal_provenance"},
]

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()

def fetch(url, source_id, attempts, timeout):
    RAW.mkdir(parents=True, exist_ok=True)
    out=RAW/(source_id+"_"+hashlib.sha256(url.encode()).hexdigest()[:12])
    last=None
    for attempt in range(1, attempts+1):
        try:
            req=Request(url,headers={"User-Agent":"REINA-SEEC/1.0","Accept":"*/*"})
            with urlopen(req,timeout=timeout,context=ssl.create_default_context()) as r, out.open("wb") as f:
                f.write(r.read())
            if out.stat().st_size == 0: raise RuntimeError("empty_response")
            return {"status":"SUCCESS","attempt":attempt,"path":str(out.relative_to(ROOT)),"sha256":sha256(out),"bytes":out.stat().st_size}
        except (HTTPError,URLError,TimeoutError,OSError,RuntimeError) as exc:
            last={"status":"FAILED","attempt":attempt,"error":f"{type(exc).__name__}: {exc}"}
            if attempt<attempts: time.sleep(min(2**attempt,20))
    return last

def search():
    attempts=[]
    for src in SOURCES:
        for url in src["urls"]:
            attempts.append({"timestamp":datetime.now(timezone.utc).isoformat(),"source_id":src["id"],"tier":src["tier"],"authority":src["authority"],"url":url,"format":src["format"],"role":src["role"],**fetch(url,src["id"],5,60)})
    result={"generated_at":datetime.now(timezone.utc).isoformat(),"election":"2023","sources":SOURCES,"attempts":attempts,"successful":[x for x in attempts if x["status"]=="SUCCESS"],"failed":[x for x in attempts if x["status"]!="SUCCESS"],"policy":{"primary_precedence":True,"vote_averaging":False,"invented_values":False}}
    ART.mkdir(parents=True,exist_ok=True); LOG.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    return result

def resolve(values):
    if not values: return {"status":"UNKNOWN","value":None,"reason":"no_evidence"}
    rank={"PRIMARY":400,"SECONDARY":200,"TERTIARY":100}
    ordered=sorted(values,key=lambda x:(rank.get(x.get("tier"),0),x.get("authority","")),reverse=True)
    top=ordered[0]
    same=[x for x in ordered if rank.get(x.get("tier"),0)==rank.get(top.get("tier"),0)]
    vals={x.get("value") for x in same}
    if len(vals)==1:
        return {"status":"RESOLVED_PRIMARY" if top.get("tier")=="PRIMARY" else "RESOLVED","value":top.get("value"),"source":top.get("source_id"),"reason":"same_tier_agreement"}
    if top.get("tier")=="PRIMARY":
        corrective=[x for x in same if x.get("role")=="official_correction"]
        if len(corrective)==1 and len(same)==2:
            return {"status":"RESOLVED_PRIMARY_CORRECTION","value":corrective[0].get("value"),"source":corrective[0].get("source_id"),"reason":"explicit_official_correction","alternatives":same}
        return {"status":"UNRESOLVED","value":None,"reason":"independent_primary_conflict","evidence":same}
    return {"status":"UNRESOLVED","value":None,"reason":"same_tier_conflict","evidence":same}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--search",action="store_true"); ap.add_argument("--resolve",action="store_true"); args=ap.parse_args()
    data=search() if args.search or not args.resolve else json.loads(LOG.read_text(encoding="utf-8"))
    print(json.dumps({"configured":len(data["sources"]),"attempts":len(data["attempts"]),"successful":len(data["successful"])},ensure_ascii=False))
    if args.resolve:
        successes=data["successful"]
        data["resolution"]={"status":"PRIMARY_EVIDENCE_AVAILABLE" if any(x["tier"]=="PRIMARY" and x["role"] in {"official_vote_matrix","official_results_and_seats"} for x in successes) else "BLOCKED_PRIMARY_UNAVAILABLE"}
        LOG.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
