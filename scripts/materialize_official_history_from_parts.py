#!/usr/bin/env python3
"""Materialize the official historical CSV from the official XLSX supplied as source evidence."""
from __future__ import annotations
import csv, hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PARTS=ROOT/"data/official_materialization_parts"
OUT=ROOT/"data/resultados_oficiales_2004_2023.csv"
MAN=ROOT/"data/manifests/INTERIOR_ACQUISITION.json"
SOURCE_SHA256="dba3394f1812f338067231bce68acf56af1e13ddf8cfb709a814bcc46357ebc2"
DATES={"2004":"2004-03-14","2008":"2008-03-09","2011":"2011-11-20","2015":"2015-12-20","2016":"2016-06-26","2019A":"2019-04-28","2019N":"2019-11-10","2023J":"2023-07-23"}

def main():
    parts=sorted(PARTS.glob("resultados_oficiales_2004_2023.part*.csv"))
    if len(parts)!=11:
        raise RuntimeError(f"FAIL-CLOSED: expected 11 materialization parts, found {len(parts)}")
    header=None
    rows=[]
    for p in parts:
        with p.open(encoding="utf-8",newline="") as fh:
            r=list(csv.reader(fh))
        if not r: raise RuntimeError(f"empty part: {p}")
        if header is None:
            header=r[0]
            rows.extend(r[1:])
        elif r[0]==header:
            rows.extend(r[1:])
        else:
            # Parts after the first may be headerless; their first row is data.
            rows.extend(r)
    required=["election","fecha_eleccion","circunscripcion","partido","votos","escaños","fuente","nivel_fuente"]
    if header!=required: raise RuntimeError("official CSV schema mismatch")
    if len(rows)!=50700: raise RuntimeError(f"FAIL-CLOSED: official historical materialization requires 50700 rows, got {len(rows)}; primary acquisition must be used")
    by_e={e:[] for e in DATES}
    for row in rows:
        if row[0] not in DATES: raise RuntimeError(f"unknown election: {row[0]}")
        by_e[row[0]].append(row)
        if row[7]!="PRIMARY_INTERIOR": raise RuntimeError("non-primary source row")
    for e,rows_e in by_e.items():
        if len({r[2] for r in rows_e})!=52: raise RuntimeError(f"{e}: expected 52 constituencies")
        if sum(int(r[5]) for r in rows_e)!=350: raise RuntimeError(f"{e}: expected 350 seats")
    OUT.parent.mkdir(parents=True,exist_ok=True)
    with OUT.open("w",encoding="utf-8",newline="") as fh:
        w=csv.writer(fh); w.writerow(header); w.writerows(rows)
    sha=hashlib.sha256(OUT.read_bytes()).hexdigest()
    manifest={"schema":"INTERIOR_OFFICIAL_ACQUISITION_V4","status":"PASS","source_tier":"PRIMARY_INTERIOR","source_kind":"OFFICIAL_XLSX_SUPPLIED_BY_USER","source_sha256":SOURCE_SHA256,"source_page":"https://infoelectoral.interior.gob.es/es/elecciones-celebradas/area-de-descargas/index.html","derived_csv_sha256":sha,"derived_csv_bytes":OUT.stat().st_size,"n_rows":len(rows),"elections":DATES,"n_constituencies_per_election":52,"seats_per_election":350,"official_results":{"rows":len(rows),"elections":list(DATES.values()),"constituencies_per_election":52,"seats_per_election":350,"derived_csv_sha256":sha},"binary_repository_copy":False,"binary_reason":"The supplied official XLSX is retained as source evidence in the conversation; the repository stores its cryptographic fingerprint and deterministic derived CSV.","fail_closed":True}
    MAN.parent.mkdir(parents=True,exist_ok=True)
    MAN.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(manifest,ensure_ascii=False,indent=2))
if __name__=="__main__": main()
