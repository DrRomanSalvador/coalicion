"""Canonical CIS historical metrics boundary.

One source of truth for CIS pre-electoral estimates (2004-2023).
No imputation, party substitution, or percentage renormalization is allowed.
"""
from __future__ import annotations
import csv
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATH = ROOT / "artifacts/data/cis_historical_2004_2023.csv"

@dataclass(frozen=True)
class CISObservation:
    election: str
    study_id: str
    study_date: str
    party: str
    vote_direct_pct: float
    cis_estimate_pct: float
    seat_range: str
    source_url: str

REQUIRED = {
    "election","study_id","study_date","party",
    "vote_direct_pct","cis_estimate_pct","seat_range","source_url","source_type",
}
ELECTIONS = ("2004","2008","2011","2015","2016","2019-04","2019-11","2023")

def load(path: str | Path = DEFAULT_PATH) -> list[CISObservation]:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"CIS historical dataset not found: {p}")
    with p.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        cols = set(reader.fieldnames or ())
        missing = REQUIRED - cols
        if missing:
            raise ValueError(f"CIS historical schema missing: {sorted(missing)}")
        rows = []
        seen = set()
        for raw in reader:
            key = (raw["election"], raw["study_id"], raw["party"])
            if key in seen:
                raise ValueError(f"duplicate CIS observation: {key}")
            seen.add(key)
            if raw["source_type"] != "PRIMARY_CIS":
                raise ValueError(f"non-primary CIS row: {key}")
            try:
                direct = float(raw["vote_direct_pct"])
                estimate = float(raw["cis_estimate_pct"])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"invalid CIS metric: {key}") from exc
            if not 0 <= direct <= 100 or not 0 <= estimate <= 100:
                raise ValueError(f"CIS metric outside [0,100]: {key}")
            if not raw["source_url"].startswith("https://www.cis.es/"):
                raise ValueError(f"non-CIS source URL: {key}")
            rows.append(CISObservation(
                raw["election"], raw["study_id"], raw["study_date"], raw["party"],
                direct, estimate, raw["seat_range"], raw["source_url"],
            ))
    if not rows:
        raise ValueError("CIS historical dataset is empty")
    if set(r.election for r in rows) != set(ELECTIONS):
        raise ValueError("CIS historical election coverage is incomplete")
    return rows

def as_oos_rows(path: str | Path = DEFAULT_PATH) -> list[dict[str, str]]:
    return [{
        "fecha_encuesta": r.study_date,
        "partido": r.party,
        "estimacion_voto": str(r.cis_estimate_pct),
        "tipo_encuesta": "preelectoral",
        "fuente": r.source_url,
        "codigo_estudio": r.study_id,
    } for r in load(path)]
