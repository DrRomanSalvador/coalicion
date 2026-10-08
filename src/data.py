"""Canonical data boundary for official Spanish election workbooks."""
from __future__ import annotations
import io, re, ssl, urllib.request
from pathlib import Path
import json
import hashlib
from datetime import datetime, timezone
from typing import Any
import certifi
import openpyxl

OFFICIAL_URL = "https://descargas.interior.gob.es/datasets/resultados_electorales/Elecciones-Congreso.xlsx"

def download_workbook(destination: str | Path, manifest: str | Path | None = None) -> Path:
    """Download the official Interior Congress dataset and optionally emit provenance."""
    dest = Path(destination)
    dest.parent.mkdir(parents=True, exist_ok=True)
    context = ssl.create_default_context(cafile=certifi.where())
    with urllib.request.urlopen(OFFICIAL_URL, context=context, timeout=60) as r:
        payload = r.read()
        content_type = r.headers.get("Content-Type", "")
    dest.write_bytes(payload)
    if not payload:
        raise RuntimeError("BLOCKED: official Interior dataset is empty")
    if manifest is not None:
        m = Path(manifest)
        m.parent.mkdir(parents=True, exist_ok=True)
        m.write_text(json.dumps({
            "schema": "OFFICIAL_SOURCE_MATERIALIZATION_V1",
            "provider": "Ministerio del Interior",
            "source_url": OFFICIAL_URL,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "content_type": content_type,
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "path": str(dest),
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return dest

def _norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())

def inspect_workbook(path: str | Path) -> dict[str, list[str]]:
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    out = {}
    for ws in wb.worksheets:
        rows = ws.iter_rows(min_row=1, max_row=min(ws.max_row, 5), values_only=True)
        headers = next(iter(rows), ())
        out[ws.title] = [str(x) for x in headers if x is not None]
    return out

def _find_col(headers, *names):
    normalized = {_norm(h): i for i, h in enumerate(headers)}
    for name in names:
        n = _norm(name)
        if n in normalized:
            return normalized[n]
    for i, h in enumerate(headers):
        n = _norm(h)
        if any(x in n for x in map(_norm, names)):
            return i
    return None

def load_rows(path: str | Path) -> list[dict[str, Any]]:
    """Load a single official electoral table without silent row loss.

    The loader fails closed on malformed numeric values and duplicate
    candidature×constituency keys. It also requires the 52 official
    constituencies; election magnitudes are validated separately by the
    canonical electoral engine.
    """
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    rows_out = []
    seen = set()
    for ws in wb.worksheets:
        it = ws.iter_rows(values_only=True)
        headers = list(next(it, ()))
        if not headers:
            continue
        pcol = _find_col(headers, "Provincia", "Circunscripción", "Province")
        partycol = _find_col(headers, "Candidatura", "Candidaturas", "Partido", "Siglas")
        votescol = _find_col(headers, "Votos", "Votos candidatura", "Candidature votes")
        if pcol is None or partycol is None or votescol is None:
            continue
        for row_number, row in enumerate(it, start=2):
            if len(row) <= max(pcol, partycol, votescol):
                raise ValueError(f"fila truncada en {ws.title}:{row_number}")
            province, party, votes = row[pcol], row[partycol], row[votescol]
            if province in (None, "") or party in (None, ""):
                raise ValueError(f"clave vacía en {ws.title}:{row_number}")
            if isinstance(votes, bool) or not isinstance(votes, (int, float)) or votes < 0:
                raise ValueError(f"votos no numéricos/no negativos en {ws.title}:{row_number}")
            if isinstance(votes, float) and not votes.is_integer():
                raise ValueError(f"votos no enteros en {ws.title}:{row_number}")
            key = (str(province).strip(), str(party).strip())
            if key in seen:
                raise ValueError(f"duplicado candidatura×circunscripción: {key}")
            seen.add(key)
            rows_out.append({
                "sheet": ws.title,
                "province": key[0],
                "party": key[1],
                "votes": int(votes),
            })
    if not rows_out:
        raise RuntimeError("No se encontró una tabla provincial/candidatura reconocible.")
    constituencies = {r["province"] for r in rows_out}
    if len(constituencies) != 52:
        raise ValueError(
            f"se requieren exactamente 52 circunscripciones; recibidas {len(constituencies)}"
        )
    return rows_out


def write_json(rows: list[dict[str, Any]], destination: str | Path) -> Path:
    dest = Path(destination)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return dest
