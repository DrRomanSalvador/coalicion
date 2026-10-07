#!/usr/bin/env python3
"""Acquire the reproducible 2004-2023 last-poll archive from a public source.

This is a SECONDARY_REPLICA staging source. It never upgrades provenance to primary.
The source page publishes 140 last polls across the eight general elections.
Technical sheets/microdata are deliberately not inferred from this table.
"""
from __future__ import annotations
import json, re
from pathlib import Path
import requests
import certifi
from bs4 import BeautifulSoup

URL = "https://www.pollingforecast.com/es/accuracy?lang=es&tab=parties"
OUT = Path("data/secondary/encuestas_historicas_last_poll_replica_2004_2023.csv")
META = Path("ci_evidence/encuestas_historicas_manifest.json")
ELECTIONS = {
    "2004": "2004", "2008": "2008", "2011": "2011", "2015": "2015",
    "2016": "2016", "abril de 2019": "2019A",
    "noviembre de 2019": "2019N", "2023": "2023",
}

def clean(v):
    if v is None:
        return None
    s = str(v).strip().replace("−", "-").replace(",", ".")
    return None if s in {"", "–", "-", "nan"} else s

def parse_polls_from_html(html_content):
    """Extrae las ocho tablas de últimas encuestas directamente del HTML."""
    soup = BeautifulSoup(html_content, "html.parser")
    candidates = []

    for table in soup.find_all("table"):
        rows = []
        for tr in table.find_all("tr"):
            cells = [c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])]
            if cells:
                rows.append(cells)
        if not rows:
            continue

        header_index = next(
            (i for i, row in enumerate(rows)
             if "Empresa" in row and "Error medio" in row),
            None,
        )
        if header_index is None:
            continue
        candidates.append((table, rows[header_index], rows[header_index + 1:]))

    if len(candidates) != len(ELECTIONS):
        raise ValueError(
            f"Se esperaban {len(ELECTIONS)} tablas de últimas encuestas y se encontraron {len(candidates)}"
        )

    fallback_order = ["2023", "2019N", "2019A", "2016", "2015", "2011", "2008", "2004"]
    rows_out = []

    for index, (table, header, body) in enumerate(candidates):
        previous = table.find_all_previous(["h2", "h3", "h4"], limit=1)
        heading_text = previous[0].get_text(" ", strip=True) if previous else ""
        election = next(
            (code for label, code in ELECTIONS.items() if label in heading_text),
            fallback_order[index],
        )

        for record in body:
            if not record:
                continue
            company_i = header.index("Empresa")
            error_i = header.index("Error medio")
            if len(record) <= company_i:
                continue
            company = clean(record[company_i])
            if not company or company == "Resultado":
                continue
            for i, party in enumerate(header):
                if i in {company_i, error_i} or i >= len(record):
                    continue
                val = clean(record[i])
                if val is None:
                    continue
                try:
                    estimate = float(val)
                except (TypeError, ValueError):
                    continue
                rows_out.append({
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

    if not rows_out:
        raise ValueError("No se encontraron observaciones de encuestas")
    return rows_out


def main():
    response = requests.get(
        URL,
        headers={"User-Agent": "Mozilla/5.0 (compatible; coalicion/2026)"},
        timeout=60,
        verify=certifi.where(),
    )
    response.raise_for_status()
    rows = parse_polls_from_html(response.content)
    # One row per poll-party observation; deterministic order.
    import pandas as pd
    df = pd.DataFrame(rows)
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
