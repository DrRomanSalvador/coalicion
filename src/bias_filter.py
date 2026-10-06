"""Selector anti-sesgos temporal, robusto y conservador.

No presupone que exista sesgo corregible. Aprende solo con información previa
a cada elección y devuelve BASE si ninguna corrección domina fuera de muestra.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from math import sqrt
from statistics import median
from typing import Callable, Sequence

@dataclass(frozen=True)
class Observation:
    election: str
    party: str
    poll: float
    actual: float
    house: str = ""
    field_end: str = ""

@dataclass(frozen=True)
class Score:
    mae: float
    rmse: float
    max_abs: float

@dataclass(frozen=True)
class Candidate:
    name: str
    predict: Callable[[Sequence[Observation], Observation], float]

def _score(errors: Sequence[float]) -> Score:
    if not errors:
        raise ValueError("No hay observaciones de validación")
    return Score(
        mae=sum(abs(x) for x in errors) / len(errors),
        rmse=sqrt(sum(x*x for x in errors) / len(errors)),
        max_abs=max(abs(x) for x in errors),
    )

def _key(x: Observation):
    # El orden temporal debe ser explícito. Si falta fecha, se rechaza:
    # nunca se permite ordenar cronológicamente por nombre de elección.
    if not x.field_end:
        raise ValueError("field_end es obligatorio para validación temporal")
    return date.fromisoformat(x.field_end)

def base(train: Sequence[Observation], obs: Observation) -> float:
    return obs.poll

def _common_bias(train: Sequence[Observation]) -> float:
    e = [x.actual - x.poll for x in train]
    return median(e) if e else 0.0

def robust_party_bias(train: Sequence[Observation], party: str, shrink_k: float = 3.0) -> float:
    e = [x.actual - x.poll for x in train if x.party == party]
    if not e:
        return _common_bias(train)
    party_bias = median(e)
    # Shrinkage conservador: una sola elección nunca equivale a evidencia fuerte.
    w = len(e) / (len(e) + shrink_k)
    return w * party_bias + (1.0 - w) * _common_bias(train)

def additive_common(train: Sequence[Observation], obs: Observation) -> float:
    return obs.poll + _common_bias(train)

def additive_party(train: Sequence[Observation], obs: Observation) -> float:
    return obs.poll + robust_party_bias(train, obs.party)

def _errors(candidate: Candidate, observations: Sequence[Observation]):
    ordered = sorted(observations, key=_key)
    elections = []
    for x in ordered:
        if x.election not in elections:
            elections.append(x.election)
    base_errors: list[float] = []
    cand_errors: list[float] = []
    for election in elections:
        test = [x for x in ordered if x.election == election]
        train = [x for x in ordered if _key(x) < min(_key(t) for t in test)]
        if not train:
            continue
        base_errors.extend(x.poll - x.actual for x in test)
        cand_errors.extend(candidate.predict(train, x) - x.actual for x in test)
    if not base_errors:
        raise ValueError("No existe ventana OOS entrenable")
    return _score(base_errors), _score(cand_errors)

def dominates(base_score: Score, candidate_score: Score) -> bool:
    no_worse = (
        candidate_score.mae <= base_score.mae
        and candidate_score.rmse <= base_score.rmse
        and candidate_score.max_abs <= base_score.max_abs
    )
    strict = (
        candidate_score.mae < base_score.mae
        or candidate_score.rmse < base_score.rmse
        or candidate_score.max_abs < base_score.max_abs
    )
    return no_worse and strict

def select_best(observations: Sequence[Observation]) -> Candidate:
    candidates = [
        Candidate("BASE", base),
        Candidate("BIAS_COMUN", additive_common),
        Candidate("BIAS_PARTIDO_SHRINK", additive_party),
    ]
    bs, _ = _errors(candidates[0], observations)
    accepted = []
    for candidate in candidates[1:]:
        _, cs = _errors(candidate, observations)
        if dominates(bs, cs):
            accepted.append((candidate, cs))
    if not accepted:
        return candidates[0]
    accepted.sort(key=lambda z: (z[1].mae, z[1].rmse, z[1].max_abs))
    return accepted[0][0]
