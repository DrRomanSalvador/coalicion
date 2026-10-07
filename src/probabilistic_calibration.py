"""Probabilistic calibration metrics; observations must be genuinely OOS."""
from __future__ import annotations
from dataclasses import dataclass
from math import sqrt


@dataclass(frozen=True)
class CalibrationSummary:
    n: int
    brier: float
    coverage: float
    mean_interval_width: float
    reliability: tuple[dict, ...]


def evaluate(
    actual: list[int],
    probabilities: list[float],
    lower: list[float] | None = None,
    upper: list[float] | None = None,
    bins: int = 10,
) -> CalibrationSummary:
    if not actual or len(actual) != len(probabilities):
        raise ValueError("actual y probabilities deben tener la misma longitud no vacía")
    if any(p < 0 or p > 1 for p in probabilities):
        raise ValueError("probabilidades fuera de [0,1]")
    if lower is None or upper is None:
        lower, upper = [0.0] * len(actual), [1.0] * len(actual)
    if len(lower) != len(actual) or len(upper) != len(actual):
        raise ValueError("intervalos incompatibles")
    if any(lo > hi for lo, hi in zip(lower, upper)):
        raise ValueError("intervalo inválido")
    brier = sum((p-y)**2 for p,y in zip(probabilities, actual)) / len(actual)
    coverage = sum(lo <= y <= hi for lo,y,hi in zip(lower,actual,upper)) / len(actual)
    width = sum(hi-lo for lo,hi in zip(lower,upper)) / len(actual)
    rel = []
    for i in range(bins):
        lo, hi = i/bins, (i+1)/bins
        idx = [j for j,p in enumerate(probabilities) if lo <= p <= hi if i == bins-1 or p < hi]
        if idx:
            rel.append({"bin": i, "n": len(idx),
                        "mean_probability": sum(probabilities[j] for j in idx)/len(idx),
                        "empirical_rate": sum(actual[j] for j in idx)/len(idx)})
    return CalibrationSummary(len(actual), brier, coverage, width, tuple(rel))
