"""Temporal decay utilities with explicit, deterministic weighting."""
from __future__ import annotations
from datetime import date
from math import exp
from typing import Sequence


def exponential_weights(
    dates: Sequence[str],
    reference_date: str | None = None,
    half_life_days: float = 365.25,
) -> list[float]:
    if half_life_days <= 0:
        raise ValueError("half_life_days debe ser positivo")
    if not dates:
        raise ValueError("se requiere al menos una fecha")
    parsed = [date.fromisoformat(x) for x in dates]
    ref = date.fromisoformat(reference_date) if reference_date else max(parsed)
    if any(d > ref for d in parsed):
        raise ValueError("no se permiten fechas futuras respecto a reference_date")
    return [exp(-((ref - d).days) / half_life_days * 0.6931471805599453) for d in parsed]


def weighted_median(values: Sequence[float], weights: Sequence[float]) -> float:
    if len(values) != len(weights) or not values:
        raise ValueError("values y weights deben tener la misma longitud no vacía")
    if any(w < 0 for w in weights) or sum(weights) <= 0:
        raise ValueError("pesos inválidos")
    pairs = sorted(zip(values, weights), key=lambda x: x[0])
    cutoff = sum(weights) / 2.0
    acc = 0.0
    for value, weight in pairs:
        acc += weight
        if acc >= cutoff:
            return float(value)
    return float(pairs[-1][0])
