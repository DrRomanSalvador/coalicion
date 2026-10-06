"""Análisis reproducible del error encuesta -> resultado electoral desde 2004.

El módulo no descarga ni inventa datos: recibe observaciones documentadas.
Cada observación es una encuesta para una elección/partido y su resultado oficial.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from math import sqrt
from statistics import median
from typing import Iterable, Sequence


@dataclass(frozen=True)
class PollObservation:
    election: str
    election_date: str
    party: str
    poll: float
    actual: float
    house: str
    field_end: str
    source: str
    poll_id: str = ""

    @property
    def error(self) -> float:
        return self.poll - self.actual

    @property
    def abs_error(self) -> float:
        return abs(self.error)

    @property
    def days_to_election(self) -> int:
        return (date.fromisoformat(self.election_date) -
                date.fromisoformat(self.field_end)).days


@dataclass(frozen=True)
class ErrorSummary:
    n: int
    mean_error: float
    median_error: float
    mae: float
    rmse: float
    minimum: float
    maximum: float
    p50_abs: float
    p80_abs: float
    p90_abs: float
    p95_abs: float


def _quantile(values: Sequence[float], q: float) -> float:
    if not values:
        raise ValueError("No hay observaciones")
    x = sorted(values)
    pos = (len(x) - 1) * q
    lo, hi = int(pos), min(int(pos) + 1, len(x) - 1)
    return x[lo] + (x[hi] - x[lo]) * (pos - lo)


def summarize(observations: Iterable[PollObservation]) -> ErrorSummary:
    rows = list(observations)
    if not rows:
        raise ValueError("No hay observaciones")
    e = [x.error for x in rows]
    ae = [abs(x) for x in e]
    return ErrorSummary(
        n=len(e),
        mean_error=sum(e) / len(e),
        median_error=median(e),
        mae=sum(ae) / len(ae),
        rmse=sqrt(sum(x*x for x in e) / len(e)),
        minimum=min(e),
        maximum=max(e),
        p50_abs=_quantile(ae, .50),
        p80_abs=_quantile(ae, .80),
        p90_abs=_quantile(ae, .90),
        p95_abs=_quantile(ae, .95),
    )


def by_election(rows: Iterable[PollObservation]) -> dict[str, ErrorSummary]:
    groups: dict[str, list[PollObservation]] = {}
    for row in rows:
        groups.setdefault(row.election, []).append(row)
    return {k: summarize(v) for k, v in sorted(groups.items())}


def by_party(rows: Iterable[PollObservation]) -> dict[str, ErrorSummary]:
    groups: dict[str, list[PollObservation]] = {}
    for row in rows:
        groups.setdefault(row.party, []).append(row)
    return {k: summarize(v) for k, v in sorted(groups.items())}


def by_house(rows: Iterable[PollObservation]) -> dict[str, ErrorSummary]:
    groups: dict[str, list[PollObservation]] = {}
    for row in rows:
        groups.setdefault(row.house, []).append(row)
    return {k: summarize(v) for k, v in sorted(groups.items())}


def by_days_to_election(rows: Iterable[PollObservation], bins: Sequence[int] = (1, 3, 7, 14, 30, 60)) -> dict[str, ErrorSummary]:
    groups: dict[str, list[PollObservation]] = {}
    for row in rows:
        d = row.days_to_election
        label = next((f"<= {b}d" for b in bins if d <= b), f"> {bins[-1]}d")
        groups.setdefault(label, []).append(row)
    return {k: summarize(v) for k, v in groups.items()}


def leave_one_election_out(rows: Sequence[PollObservation]) -> dict[str, dict[str, float]]:
    """Devuelve MAE base y MAE de una corrección simple aprendida solo antes."""
    elections = sorted({r.election for r in rows},
                       key=lambda e: min(r.election_date for r in rows if r.election == e))
    result = {}
    for election in elections:
        test = [r for r in rows if r.election == election]
        train = [r for r in rows if r.election_date < min(x.election_date for x in test)]
        if not train:
            continue
        bias = median([r.actual - r.poll for r in train])
        base_mae = sum(abs(r.poll - r.actual) for r in test) / len(test)
        corrected_mae = sum(abs(r.poll + bias - r.actual) for r in test) / len(test)
        result[election] = {
            "base_mae": base_mae,
            "corrected_mae": corrected_mae,
            "bias": bias,
        }
    return result
