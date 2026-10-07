#!/usr/bin/env python3
"""Materialize official Interior Congress historical results without R."""
from __future__ import annotations
import csv, hashlib, json, ssl, urllib.request, subprocess, tempfile, os
import certifi
from pathlib import Path
from openpyxl import load_workbook

ROOT=Path(__file__).resolve().parents[1]
URL="https://descargas.interior.gob.es/datasets/resultados_electorales/Elecciones-Congreso.xlsx"
PAGE="https://infoelectoral.interior.gob.es/es/elecciones-celebradas/area-de-descargas/index.html"
XLSX=ROOT/"data/raw/Elecciones-Congreso.xlsx"
OUT=ROOT/"data/resultados_oficiales_2004_2023.csv"
MAN=ROOT/"data/manifests/INTERIOR_ACQUISITION.json"
DATES={"2004":"2004-03-14","2008":"2008-03-09","2011":"2011-11-20","2015":"2015-12-20","2016":"2016-06-26","2019A":"2019-04-28","2019N":"2019-11-10","2023J":"2023-07-23"}

def main():
    XLSX.parent.mkdir(parents=True,exist_ok=True)
    MAN.parent.mkdir(parents=True,exist_ok=True)
    data=None
    ca_candidates=[p for p in ("/etc/ssl/certs/ca-certificates.crt", certifi.where()) if os.path.exists(p)]
    if not ca_candidates:
        raise RuntimeError("FAIL-CLOSED: no trusted CA bundle available")
    ca=ca_candidates[0]
    with tempfile.NamedTemporaryFile(suffix=".xlsx",delete=False) as tmp:
        tmp_path=Path(tmp.name)
    try:
        curl_base=["curl","-fL","--retry","4","--retry-all-errors","--retry-delay","3",
                    "--connect-timeout","30","--max-time","900","--compressed",
                    "-A","coalicion-primary-materializer/1.0"]
        for cmd in (curl_base+["-o",str(tmp_path),URL],
                    curl_base+["--cacert",ca,"-o",str(tmp_path),URL]):
            cp=subprocess.run(cmd,check=False,capture_output=True,text=True)
            if cp.returncode==0 and tmp_path.exists() and tmp_path.stat().st_size>10000:
                data=tmp_path.read_bytes()
                break
            tmp_path.unlink(missing_ok=True)
    finally:
        tmp_path.unlink(missing_ok=True)
    if data is None:
        req=urllib.request.Request(URL,headers={"User-Agent":"coalicion-primary-materializer/1.0","Referer":PAGE})
        try:
            ctx=ssl.create_default_context(cafile=ca)
            with urllib.request.urlopen(req,context=ctx,timeout=900) as r:
                data=r.read()
        except Exception:
            root_urls=[
                "https://www.cert.fnmt.es/certs/ACRAIZSERVIDORESSEGUROS.crt",
            ]
            bundle_tmp=Path(tempfile.mkstemp(suffix=".pem")[1])
            try:
                for root_url in root_urls:
                    root_tmp=Path(tempfile.mkstemp(suffix=".crt")[1])
                    root_tmps.append(root_tmp)
                    root_req=urllib.request.Request(root_url,headers={"User-Agent":"coalicion-primary-materializer/1.0"})
                    with urllib.request.urlopen(root_req,context=ssl.create_default_context(),timeout=120) as r:
                        root_tmp.write_bytes(r.read())
                    if root_tmp.stat().st_size < 1000:
                        raise RuntimeError("FAIL-CLOSED: invalid official FNMT root certificate")
                bundle_tmp.write_bytes(Path(ca).read_bytes()+b"\n"+b"\n".join(p.read_bytes() for p in root_tmps))
                ctx=ssl.create_default_context(cafile=bundle_tmp.as_posix())
                with urllib.request.urlopen(req,context=ctx,timeout=900) as r:
                    data=r.read()
            except Exception as exc:
                raise RuntimeError("FAIL-CLOSED: verified HTTPS acquisition from official Interior failed") from exc
            finally:
                for root_tmp in root_tmps:
                    root_tmp.unlink(missing_ok=True)
                bundle_tmp.unlink(missing_ok=True)
    if len(data)<=10000 or data[:4]!=b"PK\x03\x04":
        raise RuntimeError("FAIL-CLOSED: official Interior response is not a valid XLSX")
    XLSX.write_bytes(data)
    sha=hashlib.sha256(data).hexdigest()
    wb=load_workbook(XLSX,read_only=True,data_only=True)
    if "Congreso" not in wb.sheetnames: raise RuntimeError("Missing Congreso sheet")
    ws=wb["Congreso"]
    rows=ws.iter_rows(values_only=True)
    headers=next(rows)
    # Official workbook has a title/header area; locate the real header row deterministically.
    header_rows=[headers]
    while headers and not any(str(v).strip().lower()=="fecha" for v in headers if v is not None):
        headers=next(rows)
    if not headers: raise RuntimeError("Fecha header not found")
    headers=list(headers)
    def col(*names):
        for i,v in enumerate(headers):
            if str(v).strip().lower() in {n.lower() for n in names}: return i
        return -1
    date_i=col("Fecha"); desc_i=col("Descripción","Descripcion"); type_i=col("Tipo Elección","Tipo Eleccion")
    if min(date_i,desc_i,type_i)<0: raise RuntimeError("Missing required columns")
    province_cols=list(range(4,56))
    if len(province_cols)!=52: raise RuntimeError("Expected 52 constituency columns")
    provinces=[str(headers[i]).strip() for i in province_cols]
    if any(not p or p.lower()=="nan" for p in provinces) or len(set(provinces))!=52: raise RuntimeError("Invalid constituency columns")
    out=[]
    for row in rows:
        if len(row)<=max(province_cols+[date_i,desc_i,type_i]): continue
        d=row[date_i]
        ds=d.strftime("%Y-%m-%d") if hasattr(d,"strftime") else str(d)[:10]
        election=next((e for e,x in DATES.items() if x==ds),None)
        if election is None or str(row[type_i]).strip().lower()!="congreso": continue
        desc=str(row[desc_i]).strip()
        import re
        m=re.match(r"^(Votos|Escaños|Escanos|Diputados)\s*\((.*)\)$",desc,re.I)
        if not m: continue
        metric="votos" if m.group(1).lower()=="votos" else "escaños"
        party=m.group(2).strip()
        if not party: continue
        for i,p in zip(province_cols,provinces):
            v=row[i]
            if isinstance(v,(int,float)) and v>=0:
                out.append((election,DATES[election],p,party,metric,int(v)))
    if not out: raise RuntimeError("No official rows recognized")
    keys={}
    for e,d,p,party,metric,v in out:
        keys.setdefault((e,d,p,party),{})[metric]=v
    if any(set(v)!= {"votos","escaños"} for v in keys.values()): raise RuntimeError("Missing/duplicate Votos/Escaños")
    result=[]
    for (e,d,p,party),v in sorted(keys.items()):
        result.append([e,d,p,party,v["votos"],v["escaños"],"Ministerio del Interior / portal oficial de datos abiertos","PRIMARY_OFFICIAL"])
    elections=set(r[0] for r in result)
    if elections!=set(DATES): raise RuntimeError(f"Missing elections: {sorted(set(DATES)-elections)}")
    if any(sum(r[5] for r in result if r[0]==e)!=350 for e in DATES): raise RuntimeError("Historical seat totals are not 350")
    if any(len({r[2] for r in result if r[0]==e})!=52 for e in DATES): raise RuntimeError("Historical constituency totals are not 52")
    with OUT.open("w",encoding="utf-8",newline="") as f:
        w=csv.writer(f); w.writerow(["election","fecha_eleccion","circunscripcion","partido","votos","escaños","fuente","nivel_fuente"]); w.writerows(result)
    manifest={"schema":"INTERIOR_OFFICIAL_ACQUISITION_V3","status":"PASS","source_url":URL,"download_page":PAGE,"sha256":sha,"file_bytes":len(data),"elections":DATES,"n_rows":len(result),"n_constituencies_per_election":52,"source_tier":"PRIMARY_INTERIOR"}
    MAN.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(manifest,ensure_ascii=False,indent=2))

if __name__=="__main__": main()
