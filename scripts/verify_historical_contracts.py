#!/usr/bin/env python3
"""Fail-closed verification of all official historical result contracts."""
from __future__ import annotations
import csv, hashlib, json
from collections import defaultdict
from pathlib import Path
RESULTS=Path("data/resultados_oficiales_2004_2023.csv")
DATES={"2004":"2004-03-14","2008":"2008-03-09","2011":"2011-11-20","2015":"2015-12-20","2016":"2016-06-26","2019A":"2019-04-28","2019N":"2019-11-10","2023J":"2023-07-23"}
ELECTIONS=set(DATES); ROWS=50700; C=52; SEATS=350
COLS={"election","fecha_eleccion","circunscripcion","partido","votos","escaños","fuente","nivel_fuente"}
def fail(m): raise SystemExit("FAIL-CLOSED: "+m)
def main():
    if not RESULTS.is_file(): fail("official historical CSV missing")
    digest=hashlib.sha256(RESULTS.read_bytes()).hexdigest()
    with RESULTS.open(encoding="utf-8",newline="") as f: rows=list(csv.DictReader(f))
    if not rows or set(rows[0])!=COLS: fail("official CSV schema mismatch")
    if len(rows)!=ROWS: fail(f"row count {len(rows)} != {ROWS}")
    keys=set(); cs=defaultdict(set); seats=defaultdict(int); counts=defaultdict(int); votes=defaultdict(int)
    for line,r in enumerate(rows,2):
        e=r["election"]
        if e not in ELECTIONS: fail(f"unexpected election at line {line}: {e}")
        if r["fecha_eleccion"]!=DATES[e]: fail(f"wrong date at line {line}")
        if not r["circunscripcion"].strip() or not r["partido"].strip(): fail(f"blank identity at line {line}")
        try: vote=int(r["votos"]); seat=int(r["escaños"])
        except ValueError: fail(f"non-integer value at line {line}")
        if vote<0 or seat<0: fail(f"negative value at line {line}")
        if r["nivel_fuente"] not in {"PRIMARY_INTERIOR","PRIMARY_OFFICIAL"}: fail(f"non-primary row at line {line}")
        key=(e,r["circunscripcion"],r["partido"])
        if key in keys: fail(f"duplicate key at line {line}: {key}")
        keys.add(key); cs[e].add(r["circunscripcion"]); seats[e]+=seat; counts[e]+=1; votes[e]+=vote
    if set(counts)!=ELECTIONS: fail("not all eight elections are present")
    for e in sorted(ELECTIONS):
        if len(cs[e])!=C: fail(f"{e}: {len(cs[e])} constituencies != {C}")
        if seats[e]!=SEATS: fail(f"{e}: {seats[e]} seats != {SEATS}")
        if counts[e]<=0 or votes[e]<=0: fail(f"{e}: empty/zero election")
    out={"schema":"HISTORICAL_RESULTS_STRICT_CONTRACT_V1","status":"PASS","sha256":digest,"rows":len(rows),"elections":sorted(ELECTIONS),"elections_count":8,"rows_by_election":dict(sorted(counts.items())),"constituencies_per_election":{e:len(cs[e]) for e in sorted(ELECTIONS)},"seats_per_election":dict(sorted(seats.items())),"duplicate_keys":False,"future_leakage_election_rejected":"2023N" not in ELECTIONS}
    p=Path("ci_evidence/historical_results_contract.json"); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); print(json.dumps(out,ensure_ascii=False,indent=2))
if __name__=="__main__": main()
