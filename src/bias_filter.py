"""Selector anti-sesgos por validación temporal fuera de muestra.

Principio: el sesgo histórico solo se usa si una corrección demuestra utilidad
predictiva fuera de muestra frente al modelo base. No fija correcciones por
partido/casa de forma retrospectiva.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import sqrt
from statistics import median
from typing import Callable, Iterable, Sequence

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

def _score(errors: Iterable[float]) -> Score:
    e = list(errors)
    if not e:
        raise ValueError("No hay observaciones de validación")
    return Score(
        mae=sum(abs(x) for x in e) / len(e),
        rmse=sqrt(sum(x*x for x in e) / len(e)),
        max_abs=max(abs(x) for x in e),
    )

def score_candidate(
    train: Sequence[Observation],
    test: Sequence[Observation],
    candidate: Candidate,
) -> Score:
    return _score(candidate.predict(train, x) - x.actual for x in test)

def robust_party_bias(train: Sequence[Observation], party: str) -> float:
    """Mediana robusta del error poll-actual; solo con entrenamiento."""
    e = [x.actual - x.poll for x in train if x.party == party]
    return median(e) if e else 0.0

def additive_party_bias(train: Sequence[Observation], obs: Observation) -> float:
    return obs.poll + robust_party_bias(train, obs.party)

def common_bias(train: Sequence[Observation], obs: Observation) -> float:
    e = [x.actual - x.poll for x in train]
    return obs.poll + (median(e) if e else 0.0)

def base(train: Sequence[Observation], obs: Observation) -> float:
    return obs.poll

def dominates(base_score: Score, candidate_score: Score) -> bool:
    """Aceptación conservadora: no empeorar ninguna métrica y mejorar una."""
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

def rolling_leave_one_election_out(
    observations: Sequence[Observation],
    candidate: Candidate,
) -> tuple[Score, Score, bool]:
    elections = sorted({x.election for x in observations})
    base_errors: list[float] = []
    cand_errors: list[float] = []
    for election in elections:
        train = [x for x in observations if x.election < election]
        test = [x for x in observations if x.election == election]
        if not train or not test:
            continue
        b = score_candidate(train, test, Candidate("base", base))
        c = score_candidate(train, test, candidate)
        # Guardamos errores, no promedios de promedios, para ponderar cada
        # observación de forma transparente.
        base_errors.extend([x.poll - x.actual for x in test])
        cand_errors.extend([
            candidate.predict(train, x) - x.actual for x in test
        ])
    if not base_errors:
        raise ValueError("No existe ventana temporal entrenable")
    bs = _score(base_errors)
    cs = _score(cand_errors)
    return bs, cs, dominates(bs, cs)

def select_best(
    observations: Sequence[Observation],
    candidates: Sequence[Candidate],
) -> Candidate:
    """Selecciona solo por OOS; si ninguno domina al base, devuelve base."""
    base_candidate = Candidate("BASE", base)
    bs, _, _ = rolling_leave_one_election_out(observations, base_candidate)
    accepted: list[tuple[Candidate, Score]] = []
    for candidate in candidates:
        _, cs, ok = rolling_leave_one_election_out(observations, candidate)
        if ok:
            accepted.append((candidate, cs))
    if not accepted:
        return base_candidate
    accepted.sort(key=lambda item: (item[1].mae, item[1].rmse, item[1].max_abs))
    return accepted[0][0]

def guardrail(candidate: Candidate, train: Sequence[Observation]) -> Candidate:
    """Bloquea resultados no finitos y evita extrapolaciones sin evidencia."""
    for obs in train:
        value = candidate.predict(train, obs)
        if not isinstance(value, (int, float)) or not (value == value):
            return Candidate("BASE", base)
    return candidate
