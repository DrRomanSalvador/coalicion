"""Criterio de aceptación conjunto voto-escaños.

Una corrección electoral no se acepta por mejorar únicamente el porcentaje.
Debe superar al modelo base en un conjunto de métricas predefinidas sin
empeorar las demás. Las métricas de escaños se alimentan de la asignación
electoral real, nunca de una inversión escaños -> porcentaje.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import sqrt
from typing import Sequence

@dataclass(frozen=True)
class JointScore:
    vote_mae: float
    vote_rmse: float
    seat_mae: float
    seat_rmse: float
    calibration_loss: float | None = None

def _rmse(values: Sequence[float]) -> float:
    return sqrt(sum(x*x for x in values) / len(values)) if values else 0.0

def score_joint(
    vote_errors: Sequence[float],
    seat_errors: Sequence[float],
    calibration_loss: float | None = None,
) -> JointScore:
    if not vote_errors or not seat_errors:
        raise ValueError("Se necesitan errores de voto y escaños")
    return JointScore(
        vote_mae=sum(abs(x) for x in vote_errors) / len(vote_errors),
        vote_rmse=_rmse(vote_errors),
        seat_mae=sum(abs(x) for x in seat_errors) / len(seat_errors),
        seat_rmse=_rmse(seat_errors),
        calibration_loss=calibration_loss,
    )

def dominates(base: JointScore, candidate: JointScore) -> bool:
    """Pareto-conservador: ninguna métrica disponible puede empeorar."""
    fields = ["vote_mae", "vote_rmse", "seat_mae", "seat_rmse"]
    if base.calibration_loss is not None and candidate.calibration_loss is not None:
        fields.append("calibration_loss")
    no_worse = all(getattr(candidate, f) <= getattr(base, f) for f in fields)
    strict = any(getattr(candidate, f) < getattr(base, f) for f in fields)
    return no_worse and strict
