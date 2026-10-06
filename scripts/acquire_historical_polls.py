#!/usr/bin/env python3
"""Acquire the reproducible 2004-2023 last-poll archive from a public source.

This is a SECONDARY_REPLICA staging source. It never upgrades provenance to primary.
The source page publishes 140 last polls across the eight general elections.
Technical sheets/microdata are deliberately not inferred from this table.
"""
from __future__ import annotations
import json, re
from pathlib import Path
import pandas as pd

URL = "https://www.pollingforecast.com/es/accuracy?lang=es&tab=parties"
OUT = Path("data/encuestas_historicas_2004_2023.csv")
META = Path("ci_evidence/encuestas_historicas_manifest.json")
ELECTIONS = {
    "2004": "2004", "2008": "2008", "2011": "2011", "2015": "2015",
    "2016": "2016", "abril de 2019": "2019A",
    "noviembre de 2019": "2019N", "2023": "2023",
}

def clean(v):
    if pd.isna(v): return None
    s = str(v).strip().replace("−", "-").replace(",", ".")
    return None if s in {"", "–", "-", "nan"} else s

def main():
    tables = pd.read_html(URL)
    rows = []
    for t in tables:
        cols = [str(c).strip() for c in t.columns]
        if "Empresa" not in cols or not any("encuestas" in c for c in cols):
            continue
        election = None
        for c in cols:
            m = re.search(r"(2004|2008|2011|2015|2016|abril de 2019|noviembre de 2019|2023)", c)
            if m:
                election = ELECTIONS[m.group(1)]
                break
        if election is None:
            continue
        for _, r in t.iterrows():
            company = clean(r.get("Empresa"))
            if not company or company == "Resultado":
                continue
            # The table contains the latest poll of each firm before each election.
            # Party columns vary by election; retain them in long form.
            for party in cols:
                if party in {"Empresa", "Error medio"}: continue
                val = clean(r.get(party))
                if val is None: continue
                rows.append({
                    "election": election,
                    "party": party,
                    "poll": company,
                    "estimate_pct": float(val),
                    "source": URL,
                    "source_tier": "SECONDARY_REPLICA",
                    "sample_size": "",
                    "field_start": "",
                    "field_end": "",
                    "poll_id": f"{election}:{company}",
                })
    df = pd.DataFrame(rows)
    if df.empty:
        raise SystemExit("No poll tables could be parsed")
    # One row per poll-party observation; deterministic order.
    df = df.sort_values(["election","poll","party"], kind="stable")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    META.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    counts = df[["election","poll"]].drop_duplicates().groupby("election").size().to_dict()
    meta = {
        "schema": "HISTORICAL_POLLS_LAST_POLL_PER_HOUSE_V1",
        "source": URL,
        "source_tier": "SECONDARY_REPLICA",
        "elections": sorted(counts),
        "poll_count_by_election": {str(k): int(v) for k,v in counts.items()},
        "poll_count_total": int(sum(counts.values())),
        "party_observations": int(len(df)),
        "technical_microdata_status": "NOT_MATERIALIZED",
        "technical_microdata_note": "No sample size/fieldwork/method fields are inferred from the rendered result table. They require source-level fichas/microdata.",
    }
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
