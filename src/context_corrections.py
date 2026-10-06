"""Correcciones contextuales aprendidas solo con elecciones anteriores.

No afirma que exista sesgo. Cada candidato compite contra BASE fuera de muestra.
"""
from __future__ import annotations
from dataclasses import dataclass
from statistics import median
from typing import Callable, Sequence
from .poll_error import PollObservation


@dataclass(frozen=True)
class ContextScore:
    mae: float
    rmse: float
    n_elections: int


def _bias(rows: Sequence[PollObservation], key: Callable[[PollObservation], str],
          value: str, shrink: float = 3.0) -> float:
    all_e = [r.actual - r.poll for r in rows]
    group = [r.actual - r.poll for r in rows if key(r) == value]
    common = median(all_e) if all_e else 0.0
    if not group:
        return common
    w = len(group) / (len(group) + shrink)
    return w * median(group) + (1 - w) * common


def _predict(train: Sequence[PollObservation], obs: PollObservation,
             dimensions: tuple[str, ...]) -> float:
    keys = {
        "house": obs.house,
        "party": obs.party,
        "government": obs.governing_party,
        "status": obs.government_status,
    }
    def key(r: PollObservation) -> str:
        return "|".join(keys[d] if d == "government" else getattr(r, d) for d in dimensions)
    # For an interaction, learn exactly the observed context in the training data.
    value = "|".join(keys[d] for d in dimensions)
    return obs.poll + _bias(train, key, value)


def candidate_names() -> tuple[str, ...]:
    return ("BASE", "HOUSE", "PARTY", "GOVERNMENT", "HOUSE_PARTY", "GOVERNMENT_PARTY")


def predict(name: str, train: Sequence[PollObservation], obs: PollObservation) -> float:
    if name == "BASE":
        return obs.poll
    dims = {
        "HOUSE": ("house",),
        "PARTY": ("party",),
        "GOVERNMENT": ("government",),
        "HOUSE_PARTY": ("house", "party"),
        "GOVERNMENT_PARTY": ("government", "party"),
    }
    if name not in dims:
        raise ValueError(f"Candidato desconocido: {name}")
    return _predict(train, obs, dims[name])


def evaluate(rows: Sequence[PollObservation]) -> dict[str, ContextScore]:
    elections = sorted({r.election for r in rows},
                       key=lambda e: min(r.election_date for r in rows if r.election == e))
    out: dict[str, ContextScore] = {}
    for name in candidate_names():
        if name == "BASE":
            pass
        election_maes: list[float] = []
        election_rmses: list[float] = []
        seen = 0
        for election in elections:
            test = [r for r in rows if r.election == election]
            train = [r for r in rows if r.election_date < min(x.election_date for x in test)]
            if not train:
                continue
            errors = [predict(name, train, r) - r.actual for r in test]
            election_maes.append(sum(abs(x) for x in errors) / len(errors))
            election_rmses.append((sum(x*x for x in errors) / len(errors)) ** 0.5)
            seen += 1
        if not election_maes:
            continue
        out[name] = ContextScore(
            mae=sum(election_maes) / seen,
            rmse=sum(election_rmses) / seen,
            n_elections=seen,
        )
    return out


def select(rows: Sequence[PollObservation]) -> str:
    scores = evaluate(rows)
    if "BASE" not in scores:
        return "BASE"
    base = scores["BASE"]
    candidates = [
        (name, score) for name, score in scores.items()
        if name != "BASE"
        and score.mae <= base.mae
        and score.rmse <= base.rmse
        and (score.mae < base.mae or score.rmse < base.rmse)
    ]
    if not candidates:
        return "BASE"
    return min(candidates, key=lambda x: (x[1].mae, x[1].rmse))[0]
