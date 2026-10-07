"""Calibración OOS con métricas de error y estabilidad."""
from dataclasses import dataclass
from statistics import median


@dataclass(frozen=True)
class CalibrationFold:
    election: str
    train_elections: tuple[str, ...]
    actual: float
    predicted: float
    error: float


@dataclass(frozen=True)
class CalibrationSummary:
    folds: tuple[CalibrationFold, ...]
    mae: float
    rmse: float
    median_abs_error: float
    max_abs_error: float
    bias: float


def expanding_oos(observations, predictor, min_train_elections=1):
    if min_train_elections < 1 or not observations:
        raise ValueError("configuración OOS inválida")
    folds = []
    for i, (election, actual) in enumerate(observations):
        train = observations[:i]
        if len(train) < min_train_elections:
            continue
        pred = float(predictor(train))
        folds.append(CalibrationFold(
            election, tuple(e for e, _ in train), float(actual), pred, pred - float(actual)
        ))
    if not folds:
        raise ValueError("no existe ventana OOS entrenable")
    errors = [f.error for f in folds]
    absolute = [abs(e) for e in errors]
    return CalibrationSummary(
        tuple(folds),
        sum(absolute) / len(absolute),
        (sum(e * e for e in errors) / len(errors)) ** 0.5,
        median(absolute),
        max(absolute),
        sum(errors) / len(errors),
    )


def accept_update(base, candidate, max_mae_increase=0.0, max_rmse_increase=0.0):
    if candidate.mae > base.mae + max_mae_increase:
        return False
    if candidate.rmse > base.rmse + max_rmse_increase:
        return False
    return candidate.mae < base.mae or candidate.rmse < base.rmse
