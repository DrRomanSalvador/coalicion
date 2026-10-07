"""Calibración de incertidumbre para pronósticos basados en encuestas.

La superficie de error se aprende de errores históricos anteriores al corte. No
confunde dispersión entre encuestas con error electoral real y permite añadir un
componente común para encuestas correlacionadas.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from math import sqrt, log
from statistics import median
from typing import Iterable, Sequence


@dataclass(frozen=True)
class ErrorObservation:
    party: str
    election: str
    field_end: str
    election_date: str
    estimate_pct: float
    actual_pct: float


@dataclass(frozen=True)
class ErrorSurface:
    global_mae: float
    global_rmse: float
    by_party_mae: dict[str, float]
    by_party_rmse: dict[str, float]
    by_days_bucket_mae: dict[str, float]
    residual_sigma: float


def _bucket(days: int) -> str:
    if days <= 3:
        return "0-3"
    if days <= 7:
        return "4-7"
    if days <= 14:
        return "8-14"
    if days <= 30:
        return "15-30"
    if days <= 60:
        return "31-60"
    return "61+"


def calibrate_error_surface(
    observations: Iterable[ErrorObservation],
    as_of: str | None = None,
) -> ErrorSurface:
    rows = list(observations)
    if as_of is not None:
        rows = [r for r in rows if r.election_date < as_of]
    if not rows:
        raise ValueError("sin observaciones históricas para calibrar incertidumbre")
    errors = [r.estimate_pct - r.actual_pct for r in rows]
    by_party: dict[str, list[float]] = {}
    by_days: dict[str, list[float]] = {}
    for r in rows:
        days = (date.fromisoformat(r.election_date) - date.fromisoformat(r.field_end)).days
        by_party.setdefault(r.party, []).append(r.estimate_pct - r.actual_pct)
        by_days.setdefault(_bucket(max(0, days)), []).append(r.estimate_pct - r.actual_pct)
    return ErrorSurface(
        global_mae=sum(abs(x) for x in errors) / len(errors),
        global_rmse=sqrt(sum(x*x for x in errors) / len(errors)),
        by_party_mae={p: sum(abs(x) for x in xs) / len(xs) for p, xs in by_party.items()},
        by_party_rmse={p: sqrt(sum(x*x for x in xs) / len(xs)) for p, xs in by_party.items()},
        by_days_bucket_mae={b: sum(abs(x) for x in xs) / len(xs) for b, xs in by_days.items()},
        residual_sigma=max(0.1, sqrt(sum((x - median(errors))**2 for x in errors) / len(errors))),
    )


def party_sigma(
    surface: ErrorSurface,
    party: str,
    days_to_election: int,
    common_error_share: float = 0.35,
) -> float:
    """Estimación conservadora del sigma del error de voto en puntos porcentuales."""
    if not 0 <= common_error_share < 1:
        raise ValueError("common_error_share debe estar en [0,1)")
    base = surface.by_party_rmse.get(party, surface.global_rmse)
    bucket_mae = surface.by_days_bucket_mae.get(_bucket(max(0, days_to_election)))
    if bucket_mae is not None:
        base = max(base, bucket_mae)
    return max(0.1, base * (1.0 + common_error_share))


def normal_interval(center: float, sigma: float, confidence: float = 0.90) -> tuple[float, float]:
    """Intervalo normal aproximado; la calibración de cobertura debe hacerse OOS."""
    if sigma <= 0:
        raise ValueError("sigma debe ser positivo")
    z = {0.50: 0.67448975, 0.80: 1.28155157, 0.90: 1.64485363, 0.95: 1.95996398}.get(confidence)
    if z is None:
        raise ValueError("confidence debe ser 0.50, 0.80, 0.90 o 0.95")
    return max(0.0, center-z*sigma), min(100.0, center+z*sigma)


def calibrate_coverage(
    forecasts: Sequence[tuple[float, float, float, float]],
) -> dict[str, float]:
    """Evalúa cobertura 50/80/90/95 de intervalos (low,high,actual)."""
    if not forecasts:
        raise ValueError("sin intervalos")
    out = {}
    for level, idx in ((50, 0), (80, 1), (90, 2), (95, 3)):
        # tuples: low50,high50,low80,high80,...,actual
        covered = 0
        for row in forecasts:
            low, high = row[idx*2], row[idx*2+1]
            actual = row[-1]
            covered += int(low <= actual <= high)
        out[f"coverage_{level}"] = covered / len(forecasts)
    return out
