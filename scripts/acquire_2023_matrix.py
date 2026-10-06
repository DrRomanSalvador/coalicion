#!/usr/bin/env python3
"""Acquire and validate the complete 2023 Congress constituency matrix."""
from __future__ import annotations
import hashlib, json, re, ssl, time
from pathlib import Path
from urllib.request import Request, urlopen

OFFICIAL_XLSX = "https://descargas.interior.gob.es/datasets/resultados_electorales/Elecciones-Congreso.xlsx"
SECONDARY_BASE = "https://datoelectoral.es/circunscripciones/"
SLUGS = {"Madrid":37,"Barcelona":32,"Valencia/València":16,"Alicante/Alacant":12,"Sevilla":12,"Málaga":11,"Murcia":10,"Cádiz":9,"A Coruña":8,"Balears, Illes":8,"Bizkaia":8,"Las Palmas":8,"Asturias":7,"Granada":7,"Pontevedra":7,"Santa Cruz de Tenerife":7,"Zaragoza":7,"Almería":6,"Córdoba":6,"Gipuzkoa":6,"Girona":6,"Tarragona":6,"Toledo":6,"Badajoz":5,"Cantabria":5,"Castellón/Castelló":5,"Ciudad Real":5,"Huelva":5,"Jaén":5,"Navarra":5,"Valladolid":5,"Albacete":4,"Araba/Álava":4,"Burgos":4,"Cáceres":4,"La Rioja":4,"León":4,"Lleida":4,"Lugo":4,"Ourense":4,"Salamanca":4,"Ávila":3,"Cuenca":3,"Guadalajara":3,"Huesca":3,"Palencia":3,"Segovia":3,"Teruel":3,"Zamora":3,"Soria":2,"Ceuta":1,"Melilla":1}

def fetch(url, attempts=5):
    last=None
    for i in range(attempts):
        try:
            ctx=ssl.create_default_context()
            req=Request(url,headers={"User-Agent":"coalicion/2026 matrix-acquirer"})
            with urlopen(req,timeout=45,context=ctx) as r: return r.read(), "CERT_VALIDATED"
        except Exception as e:
            last=e; time.sleep(min(2**i,10))
    raise RuntimeError(f"download failed: {url}: {last}")

def slug(name):
    x=name.lower()
    table=str.maketrans("áéíóúüñ","aeiouun")
    x=x.translate(table).replace("/","-")
    return re.sub(r"[^a-z0-9]+","-",x).strip("-")

def parse_secondary(raw, province, seats):
    text=raw.decode("utf-8","replace")
    table=re.search(r"<table[\s\S]*?</table>",text,re.I)
    if not table: raise ValueError(f"candidate table missing: {province}")
    cells=re.findall(r"<(?:td|th)[^>]*>([\s\S]*?)</(?:td|th)>",table.group(0),re.I)
    clean=[re.sub(r"\\s+"," ",re.sub(r"<[^>]+>"," ",x)).strip() for x in cells]
    start=next((i for i,x in enumerate(clean) if x=="Candidatura"),None)
    if start is None: raise ValueError(f"candidate header missing: {province}")
    parties={}; blank=0; valid=None
    for i in range(start+3,len(clean)-2,3):
        name,votes,pct=clean[i:i+3]
        digits=re.sub(r"[^0-9]","",votes)
        if not digits: continue
        n=int(digits)
        if name.lower().startswith("votos en blanco"): blank=n
        elif name.lower().startswith("total votos válidos"): valid=n
        else: parties[name]=n
    if valid is None: valid=sum(parties.values())+blank
    return {"seats":seats,"parties":parties,"blank_votes":blank,"valid_votes":valid,"source_url":SECONDARY_BASE+slug(province)}

def build_from_official(raw, root):
    import tempfile
    from src.data_pipeline import load_rows
    p=root/"artifacts/data/raw_2023_interior.xlsx"
    p.write_bytes(raw)
    rows=load_rows(p)
    matrix={}
    for row in rows:
        c=row["province"]
        matrix.setdefault(c,{"seats":SLUGS.get(c),"parties":{},"blank_votes":0})
        matrix[c]["parties"][row["party"]]=row["votes"]
    return matrix

def validate(matrix,national):
    errors=[]
    if set(matrix)!=set(SLUGS): errors.append(f"circunscripciones: {len(matrix)}/52")
    if sum(x.get("seats") or 0 for x in matrix.values())!=350: errors.append("escaños != 350")
    for c,x in matrix.items():
        if x.get("seats")!=SLUGS.get(c): errors.append(f"escaños incorrectos: {c}")
        if any(not isinstance(v,int) or v<0 for v in x["parties"].values()): errors.append(f"votos inválidos: {c}")
    candidate_total=sum(sum(x["parties"].values()) for x in matrix.values())
    if candidate_total!=national["candidate_ballots"]: errors.append(f"total candidaturas {candidate_total} != {national['candidate_ballots']}")
    return {"valid":not errors,"errors":errors,"circunscripciones":len(matrix),"escaños":sum(x.get("seats") or 0 for x in matrix.values()),"candidate_votes_total":candidate_total}

def main():
    root=Path(__file__).resolve().parents[1]
    data_dir=root/"artifacts/data"; data_dir.mkdir(parents=True,exist_ok=True)
    national=json.loads((data_dir/"election_2023_national.json").read_text(encoding="utf-8"))
    events=[]; matrix=None
    try:
        raw,method=fetch(OFFICIAL_XLSX)
        digest=hashlib.sha256(raw).hexdigest()
        matrix=build_from_official(raw,root)
        validation=validate(matrix,national)
        events.append({"source":"MINISTERIO_DEL_INTERIOR","status":"DOWNLOADED_AND_PARSED","method":method,"sha256":digest,"validation":validation})
        if not validation["valid"]: raise RuntimeError("OFFICIAL_MATRIX_VALIDATION_FAILED")
        tier="OFFICIAL_PRIMARY"
    except Exception as e:
        events.append({"source":"MINISTERIO_DEL_INTERIOR","status":"FAILED","error":str(e)})
        matrix={}
        for province,seats in SLUGS.items():
            raw,_=fetch(SECONDARY_BASE+slug(province),attempts=3)
            matrix[province]=parse_secondary(raw,province,seats)
        validation=validate(matrix,national)
        tier="SECONDARY_REPLICA_VERIFIED"
        events.append({"source":"DATO_ELECTORAL","status":"DOWNLOADED_AND_PARSED","validation":validation})
        if not validation["valid"]: raise SystemExit("MATRIX_VALIDATION_FAILED")
    canonical={"schema":"ELECTION_2023_CONSTITUENCY_MATRIX_V1","election":2023,"type":"general","source_tier":tier,"data":{"constituencies":dict(sorted(matrix.items()))},"validation":validation}
    (data_dir/"election_2023_canonical.json").write_text(json.dumps(canonical,ensure_ascii=False,indent=2),encoding="utf-8")
    (data_dir/"election_2023_matrix_acquisition.json").write_text(json.dumps({"status":"READY","events":events,"source_tier":tier,"sha256":events[-1].get("sha256")},ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"status":"READY","source_tier":tier,"circunscripciones":validation["circunscripciones"],"escaños":validation["escaños"]},ensure_ascii=False))
if __name__=="__main__": main()
