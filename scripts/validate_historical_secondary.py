#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd

p = Path(".audit_historico/historical_province_secondary.csv")
if not p.exists():
    raise SystemExit("Missing staged historical dataset")

df = pd.read_csv(p)
required = {
    "election", "prov", "blank_ballots", "invalid_ballots",
    "party_ballots", "valid_ballots", "total_ballots", "ballots"
}
missing = sorted(required - set(df.columns))
if missing:
    raise SystemExit(f"Missing required columns: {missing}")

df["ballots"] = pd.to_numeric(df["ballots"], errors="coerce")
for c in ["blank_ballots","invalid_ballots","party_ballots","valid_ballots","total_ballots"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

group = (
    df.groupby(["election","prov"], dropna=False)
      .agg(
          party_sum=("ballots","sum"),
          party_ballots=("party_ballots","first"),
          blank=("blank_ballots","first"),
          valid=("valid_ballots","first"),
          invalid=("invalid_ballots","first"),
          total=("total_ballots","first"),
      )
      .reset_index()
)

group["diff_party"] = group["party_sum"] - group["party_ballots"]
group["diff_valid"] = group["valid"] - (group["party_ballots"] + group["blank"])
group["diff_total"] = group["total"] - (group["valid"] + group["invalid"])

bad = group[
    (group["diff_party"].abs() > 0.5)
    | (group["diff_valid"].abs() > 0.5)
    | (group["diff_total"].abs() > 0.5)
]

counts = group.groupby("election")["prov"].nunique().to_dict()
expected = 52
bad_counts = {k:int(v) for k,v in counts.items() if int(v) != expected}

result = {
    "status": "PASS" if bad.empty and not bad_counts else "FAIL",
    "source_tier": "SECONDARY_REPLICA",
    "elections": sorted(map(str, group["election"].unique())),
    "province_election_cells": int(len(group)),
    "province_count_by_election": {str(k): int(v) for k,v in counts.items()},
    "expected_provinces_per_election": expected,
    "arithmetic_bad_cells": int(len(bad)),
    "province_count_failures": bad_counts,
}
Path(".audit_historico/validation.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(json.dumps(result, ensure_ascii=False, indent=2))
if result["status"] != "PASS":
    raise SystemExit("Historical arithmetic validation FAILED")
