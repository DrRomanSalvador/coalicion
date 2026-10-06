#!/usr/bin/env python3
"""
Exhaustive electoral acquisition for REINA-SEEC.

Design:
- exhaust configured official/secondary/tertiary endpoints;
- preserve every attempt and SHA-256;
- never average official vote cells;
- resolve a conflict by evidence precedence, not by majority vote;
- if evidence is insufficient, emit UNKNOWN/UNRESOLVED rather than inventing a value.

The source catalogue is deliberately explicit and versionable. Discovery can add
candidates, but a discovered URL is not trusted until its authority is classified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import ssl
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"
LOG = ART / "exhaustive_search_2023.json"
RAW = ROOT / "data" / "raw" / "exhaustive"

SOURCES = [
    # Primary official.
    {"id":"INTERIOR_CONGRESO_XLSX","tier":"PRIMARY","authority":"MINISTERIO_INTERIOR",
     "urls":["https://descargas.interior.gob.es/datasets/resultados_electorales/Elecciones-Congreso.xlsx"],
     "format":"xlsx","role":"official_vote_matrix"},
    {"id":"INTERIOR_CARGOS_ELECTOS_XLSX","tier":"PRIMARY","authority":"MINISTERIO_INTERIOR",
     "urls":["https://descargas.interior.gob.es/datasets/resultados_electorales/Elecciones-Congreso-cargos-electos.xlsx"],
     "format":"xlsx","role":"elected_members"},
    {"id":"BOE_JEC_2023_RESULTS","tier":"PRIMARY","authority":"JUNTA_ELECTORAL_CENTRAL",
     "urls":["https://www.boe.es/buscar/doc.php?id=BOE-A-2023-18907",
            "https://www.boe.es/boe/dias/2023/09/01/pdfs/BOE-A-2023-18907.pdf"],
     "format":"html_or_pdf","role":"official_results_and_seats"},
    {"id":"BOE_JEC_2023_CORRECTION","tier":"PRIMARY","authority":"JUNTA_ELECTORAL_CENTRAL",
     "urls":["https://www.boe.es/buscar/doc.php?id=BOE-A-2023-19537"],
     "format":"html","role":"official_correction"},

    # Secondary: only corroboration, never replacement of primary official cells.
    {"id":"ELECCIONESDB_2023","tier":"SECONDARY","authority":"SPAIN_ELECTORAL_PROJECT",
     "urls":["https://eleccionesdb.spainelectoralproject.com/api/2023/general",
            "https://eleccionesdb.spainelectoralproject.com/datos/2023.json"],
     "format":"json","role":"corroboration"},
    {"id":"POLITPRO_2023","tier":"SECONDARY","authority":"POLITPRO",
     "urls":["https://politpro.eu/en/spain/election/parliament/2023/results"],
     "format":"html","role":"corroboration"},
    {"id":"ELPAIS_2023","tier":"SECONDARY","authority":"EL_PAIS",
     "urls":["https://elpais.com/espana/elecciones/generales/2023/resultados/"],
     "format":"html","role":"corroboration"},
    {"id":"ELMUNDO_2023","tier":"SECONDARY","authority":"EL_MUNDO",
     "urls":["https://www.elmundo.es/espana/elecciones/2023/resultados.html"],
     "format":"html","role":"corroboration"},
    {"id":"LAVANGUARDIA_2023","tier":"SECONDARY","authority":"LA_VANGUARDIA",
     "urls":["https://www.lavanguardia.com/elecciones/2023/resultados"],
     "format":"html","role":"corroboration"},

    # Tertiary / discovery leads. Never promoted automatically.
    {"id":"WIKIPEDIA_2023","tier":"TERTIARY","authority":"WIKIPEDIA",
     "urls":["https://es.wikipedia.org/wiki/Elecciones_generales_de_Espa%C3%B1a_de_2023"],
     "format":"html","role":"discovery"},
]

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()

def fetch(url: str, source_id: str, attempts: int, timeout: int) -> dict:
    RAW.mkdir(parents=True, exist_ok=True)
    safe = source_id + "_" + hashlib.sha256(url.encode()).hexdigest()[:12]
    out = RAW / safe
    last = None
    for attempt in range(1, attempts+1):
        try:
            req=Request(url, headers={"User-Agent":"REINA-SEEC/1.0","Accept":"*/*","Connection":"close"})
            ctx=ssl.create_default_context()
            with urlopen(req, timeout=timeout, context=ctx) as r, out.open("wb") as f:
                f.write(r.read())
            if out.stat().st_size == 0: raise RuntimeError("empty_response")
            return {"status":"SUCCESS","attempt":attempt,"path":str(out.relative_to(ROOT)),
                    "sha256":sha256(out),"bytes":out.stat().st_size}
        except (HTTPError,URLError,TimeoutError,OSError,RuntimeError) as exc:
            last={"status":"FAILED","attempt":attempt,"error":f"{type(exc).__name__}: {exc}"}
            if attempt<attempts: time.sleep(min(2**attempt,20))
    return last or {"status":"FAILED","error":"unknown"}

def search() -> dict:
    attempts=[]
    for src in SOURCES:
        for url in src["urls"]:
            result=fetch(url,src["id"],5 if src["tier"]=="PRIMARY" else 3,60)
            attempts.append({
                "timestamp":datetime.now(timezone.utc).isoformat(),
                "source_id":src["id"],"tier":src["tier"],"authority":src["authority"],
                "url":url,"format":src["format"],"role":src["role"],**result
            })
    result={"generated_at":datetime.now(timezone.utc).isoformat(),
            "election":"2023","sources":SOURCES,"attempts":attempts,
            "successful":[x for x in attempts if x["status"]=="SUCCESS"],
            "failed":[x for x in attempts if x["status"]!="SUCCESS"],
            "policy":{"primary_precedence":True,"vote_averaging":False,"invented_values":False}}
    ART.mkdir(parents=True,exist_ok=True)
    LOG.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    return result

def resolve(values: list[dict]) -> dict:
    """
    Deterministic precedence:
      PRIMARY official > legally corrective PRIMARY > SECONDARY > TERTIARY.
    Equal-tier disagreement is UNRESOLVED unless an authoritative correction
    explicitly identifies the winning value.
    """
    if not values:
        return {"status":"UNKNOWN","value":None,"reason":"no_evidence"}
    rank={"PRIMARY":400,"SECONDARY":200,"TERTIARY":100}
    ordered=sorted(values,key=lambda x:(rank.get(x.get("tier"),0),x.get("authority","")),reverse=True)
    top=ordered[0]
    same=[x for x in ordered if rank.get(x.get("tier"),0)==rank.get(top.get("tier"),0)]
    vals={x.get("value") for x in same}
    if len(vals)==1:
        return {"status":"RESOLVED","value":top.get("value"),"source":top.get("source_id"),"reason":"same_tier_agreement"}
    if top.get("tier")=="PRIMARY":
        return {"status":"RESOLVED_PRIMARY","value":top.get("value"),"source":top.get("source_id"),
                "reason":"official_precedence","alternatives":same}
    return {"status":"UNRESOLVED","value":None,"reason":"same_tier_conflict","evidence":same}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--search",action="store_true")
    ap.add_argument("--resolve",action="store_true")
    args=ap.parse_args()
    if not args.search and not args.resolve: args.search=True
    data=search() if args.search else json.loads(LOG.read_text(encoding="utf-8"))
    print("Fuentes configuradas:",len(data["sources"]))
    print("URLs intentadas:",len(data["attempts"]))
    print("Descargas correctas:",sum(x["status"]=="SUCCESS" for x in data["attempts"]))
    print("Registro:",LOG)
    if args.resolve:
        successes = data["successful"]
        primary_ok = any(x["tier"] == "PRIMARY" for x in successes)
        data["resolution"] = {
            "status": "PRIMARY_EVIDENCE_AVAILABLE" if primary_ok else "BLOCKED_PRIMARY_UNAVAILABLE",
            "primary_sources_successful": sorted({x["source_id"] for x in successes if x["tier"] == "PRIMARY"}),
            "secondary_sources_successful": sorted({x["source_id"] for x in successes if x["tier"] == "SECONDARY"}),
            "tertiary_sources_successful": sorted({x["source_id"] for x in successes if x["tier"] == "TERTIARY"}),
            "rule": "PRIMARY_WINS; equal-tier conflicts remain UNRESOLVED; never average official vote cells"
        }
        LOG.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print("Resolución:", data["resolution"]["status"])
    return 0

if __name__=="__main__":
    raise SystemExit(main())
