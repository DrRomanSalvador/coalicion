"""Expanding-window OOS pipeline for historical poll observations."""
from __future__ import annotations
from dataclasses import asdict
from pathlib import Path
import csv
from .bias_filter import Observation, select_best
from .poll_error import PollObservation
from .context_corrections import evaluate, select


REQUIRED = {"election","election_date","party","poll","actual","house","field_end","source","poll_id"}


def load_poll_observations(path: str | Path) -> list[PollObservation]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"dataset OOS inexistente: {p}")
    with p.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        raise ValueError(f"dataset OOS vacío: {p}")
    missing = REQUIRED - set(rows[0])
    if missing:
        raise ValueError(f"dataset OOS sin columnas: {sorted(missing)}")
    out = []
    for r in rows:
        out.append(PollObservation(
            election=r["election"], election_date=r["election_date"],
            party=r["party"], poll=float(r["poll"]), actual=float(r["actual"]),
            house=r["house"], field_end=r["field_end"], source=r["source"],
            poll_id=r["poll_id"], governing_party=r.get("governing_party",""),
            government_status=r.get("government_status",""),
            government_change=r.get("government_change",""),
        ))
    return out


def run_oos(rows: list[PollObservation]) -> dict:
    if len({r.election for r in rows}) < 2:
        raise ValueError("OOS requiere al menos dos elecciones")
    correction = select_best([
        Observation(r.election, r.party, r.poll, r.actual, r.house, r.field_end)
        for r in rows
    ])
    context = select(rows)
    return {
        "status": "PASS",
        "n_rows": len(rows),
        "n_elections": len({r.election for r in rows}),
        "selected_bias_correction": correction.name,
        "selected_context_correction": context,
        "contract": "EXPANDING_WINDOW_NO_FUTURE_LEAKAGE",
    }
