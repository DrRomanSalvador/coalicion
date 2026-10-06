#!/usr/bin/env python3
"""Extract official Interior Congress workbook into a versioned historical staging dataset.

Fail-closed: does not guess column meanings. It records workbook/sheet schema and
only emits canonical rows after required semantic columns are identified.
"""
from __future__ import annotations
import hashlib, json, re
from pathlib import Path
import pandas as pd

SRC=Path(".audit_historico/Elecciones-Congreso.xlsx")
OUT=Path(".audit_historico")
OUT.mkdir(parents=True, exist_ok=True)

if not SRC.exists():
    raise SystemExit("Missing official Interior workbook")

sha=hashlib.sha256(SRC.read_bytes()).hexdigest()
(OUT/"source.sha256").write_text(f"{sha}  {SRC.name}\n", encoding="utf-8")

sheets=pd.read_excel(SRC, sheet_name=None, engine="openpyxl")
schema={}
for name,df in sheets.items():
    schema[name]={
        "rows":int(len(df)),
        "columns":[str(c) for c in df.columns],
        "dtypes":{str(c):str(t) for c,t in df.dtypes.items()},
    }
(OUT/"schema.json").write_text(json.dumps(schema,ensure_ascii=False,indent=2),encoding="utf-8")

# Export each sheet as CSV without altering values, for reproducibility/audit.
for i,(name,df) in enumerate(sheets.items()):
    safe=re.sub(r"[^A-Za-z0-9_.-]+","_",str(name)).strip("_") or f"sheet_{i}"
    df.to_csv(OUT/f"raw_{i:02d}_{safe}.csv",index=False)

print("WORKBOOK_SHA256",sha)
print("SHEETS",list(sheets))
for name,df in sheets.items():
    print("SHEET",repr(name),"ROWS",len(df),"COLS",list(map(str,df.columns)))
