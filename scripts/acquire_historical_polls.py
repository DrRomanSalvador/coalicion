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
import requests
from bs4 import BeautifulSoup

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

def parse_polls_from_html(html_content):
    """Extrae las tablas de últimas encuestas del HTML actual, sin depender de clases CSS."""
    soup = BeautifulSoup(html_content, "html.parser")
    rows = []
    parsed_tables = 0

    for table in soup.find_all("table"):
        try:
            frames = pd.read_html(str(table))
        except (ValueError, ImportError):
            continue
        if not frames:
            continue
        t = frames[0]
        cols = [str(c).strip() for c in t.columns]
        if "Empresa" not in cols or "Error medio" not in cols:
            continue

        # El formato actual pone "2023 · 22 encuestas", etc., justo antes de la tabla.
        heading = table.find_previous(["h2", "h3", "h4"])
        heading_text = heading.get_text(" ", strip=True) if heading else ""
        election = None
        for label, code in ELECTIONS.items():
            if label in heading_text:
                election = code
                break
        if election is None:
            continue

        parsed_tables += 1
        for _, record in t.iterrows():
            company = clean(record.get("Empresa"))
            if not company or company == "Resultado":
                continue
            for party in cols:
                if party in {"Empresa", "Error medio"}:
                    continue
                val = clean(record.get(party))
                if val is None:
                    continue
                try:
                    estimate = float(val)
                except (TypeError, ValueError):
                    continue
                rows.append({
                    "election": election,
                    "party": party,
                    "poll": company,
                    "estimate_pct": estimate,
                    "source": URL,
                    "source_tier": "SECONDARY_REPLICA",
                    "sample_size": "",
                    "field_start": "",
                    "field_end": "",
                    "poll_id": f"{election}:{company}",
                })

    if parsed_tables != len(ELECTIONS):
        raise ValueError(
            f"Se esperaban {len(ELECTIONS)} tablas electorales y se encontraron {parsed_tables}"
        )
    if not rows:
        raise ValueError("No se encontraron observaciones de encuestas")
    return rows

def main():
    response = requests.get(
        URL,
        headers={"User-Agent": "Mozilla/5.0 (compatible; coalicion/2026)"},
        timeout=60,
        verify=True,
    )
    response.raise_for_status()
    rows = parse_polls_from_html(response.content)
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
