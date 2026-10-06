#!/usr/bin/env python3
"""Secondary historical staging from pollspaindata.

This is NOT the primary Interior source. It is a reproducible fallback when
the official Interior download is unreachable from CI. The resulting evidence
is explicitly tagged SECONDARY and must not be treated as primary-source
certification.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

import pandas as pd
import pyreadr

ROOT = Path(".audit_historico")
ROOT.mkdir(parents=True, exist_ok=True)

URL = (
    "https://raw.githubusercontent.com/dadosdelaplace/pollspaindata/"
    "main/inst/extdata/summary_elec/summary_elec_prov_2023-07-24.rda"
)
TARGET_DATES = {
    "2004-03-14": "2004",
    "2008-03-09": "2008",
    "2011-11-20": "2011",
    "2015-12-20": "2015",
    "2016-06-26": "2016",
    "2019-04-28": "2019A",
    "2019-11-10": "2019N",
    "2023-07-24": "2023",
}

out = ROOT / "secondary_pollspaindata.rda"
req = Request(URL, headers={"User-Agent": "SEEC-historical-staging/1.0"})
with urlopen(req, timeout=60) as resp:
    out.write_bytes(resp.read())

sha = hashlib.sha256(out.read_bytes()).hexdigest()
(ROOT / "secondary.sha256").write_text(f"{sha}  {out.name}\n", encoding="utf-8")

objects = pyreadr.read_r(str(out))
if not objects:
    raise RuntimeError("No R objects found in secondary source")

frames = []
for name, df in objects.items():
    if isinstance(df, pd.DataFrame):
        frames.append(df)

if not frames:
    raise RuntimeError("Secondary RDA contained no tabular object")

df = max(frames, key=len).copy()
(ROOT / "secondary_schema.json").write_text(
    json.dumps(
        {
            "source": URL,
            "source_tier": "SECONDARY_REPLICA",
            "sha256": sha,
            "object_names": list(objects),
            "rows": int(len(df)),
            "columns": list(df.columns),
            "dtypes": {c: str(t) for c, t in df.dtypes.items()},
        },
        ensure_ascii=False,
        indent=2,
        default=str,
    ),
    encoding="utf-8",
)

# Preserve the source table unchanged.
df.to_csv(ROOT / "secondary_prov_raw.csv", index=False)

date_col = next((c for c in ("date", "fecha") if c in df.columns), None)
if date_col is not None:
    df["_date_iso"] = pd.to_datetime(df[date_col], errors="coerce").dt.strftime("%Y-%m-%d")
elif "id_elec" in df.columns:
    # pollspaindata encodes Congress election date as 02-YYYY-MM-DD.
    df["_date_iso"] = (
        df["id_elec"].astype(str)
        .str.extract(r"(\d{4}-\d{2}-\d{2})", expand=False)
    )
else:
    raise RuntimeError(f"No election-date field found; columns={list(df.columns)}")
sel = df[df["_date_iso"].isin(TARGET_DATES)].copy()
if sel.empty:
    raise RuntimeError("No target elections found in secondary source")

sel["election"] = sel["_date_iso"].map(TARGET_DATES)
sel.to_csv(ROOT / "historical_province_secondary.csv", index=False)

manifest = {
    "source": URL,
    "source_tier": "SECONDARY_REPLICA",
    "source_sha256": sha,
    "target_elections": list(TARGET_DATES.values()),
    "rows_selected": int(len(sel)),
    "note": (
        "Derived from pollspaindata, which documents Spanish electoral data "
        "downloaded from the Ministry of the Interior. Primary-source "
        "certification remains blocked until the official Interior file is "
        "retrieved and cross-checked."
    ),
}
(ROOT / "secondary_manifest.json").write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
)

print(json.dumps(manifest, ensure_ascii=False, indent=2))
print("COLUMNS:", list(df.columns))
