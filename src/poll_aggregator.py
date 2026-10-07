"""Agregador de encuestas auditable inspirado en la metodología pública de Kiko Llaneras.

No fija pesos arbitrarios ni inventa microdatos. Los parámetros son explícitos y pueden
calibrarse exclusivamente con elecciones anteriores. El agregador devuelve tanto la
estimación como el desglose de pesos, correcciones y diagnósticos.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import date
from math import exp
from statistics import median
from typing import Iterable, Sequence


@dataclass(frozen=True)
class PollEstimate:
    election: str
    party: str
    house: str
    estimate_pct: float
    field_end: str
    sample_size: int
    poll_id: str
    source: str = ""
    source_tier: str = ""


@dataclass(frozen=True)
class HistoricalError:
    election: str
    party: str
    house: str
    estimate_pct: float
    actual_pct: float
    field_end: str
    election_date: str


@dataclass(frozen=True)
class AggregationConfig:
    sample_exponent: float = 0.5
    recency_half_life_days: float = 30.0
    history_strength: float = 8.0
    house_shrinkage: float = 10.0
    repeated_house_penalty: float = 0.65
    min_history_observations: int = 3
    min_weight: float = 1e-9
    max_days_old: int = 120


@dataclass(frozen=True)
class WeightedPoll:
    poll_id: str
    house: str
    party: str
    raw_estimate_pct: float
    corrected_estimate_pct: float
    weight: float
    sample_component: float
    recency_component: float
    history_component: float
    house_component: float
    repetition_component: float
    days_old: int


@dataclass(frozen=True)
class AggregatedParty:
    party: str
    estimate_pct: float
    lower_bound_pct: float
    upper_bound_pct: float
    effective_polls: float
    weighted_observations: tuple[WeightedPoll, ...]


def _days(a: str, b: str) -> int:
    return (date.fromisoformat(a) - date.fromisoformat(b)).days


def _mean(xs: Sequence[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _quantile(xs: Sequence[float], q: float) -> float:
    if not xs:
        return 0.0
    ys = sorted(xs)
    pos = (len(ys) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(ys) - 1)
    return ys[lo] + (ys[hi] - ys[lo]) * (pos - lo)


def _validate_poll(p: PollEstimate) -> None:
    if not p.party or not p.house or not p.poll_id:
        raise ValueError("encuesta incompleta: party/house/poll_id son obligatorios")
    if not 0 <= p.estimate_pct <= 100:
        raise ValueError(f"{p.poll_id}/{p.party}: estimación fuera de [0,100]")
    if p.sample_size <= 0:
        raise ValueError(f"{p.poll_id}: sample_size debe ser positivo")
    date.fromisoformat(p.field_end)


def _house_party_stats(
    historical: Sequence[HistoricalError], config: AggregationConfig
) -> dict[tuple[str, str], tuple[float, float, int]]:
    groups: dict[tuple[str, str], list[float]] = {}
    for row in historical:
        groups.setdefault((row.house, row.party), []).append(
            row.estimate_pct - row.actual_pct
        )
    out = {}
    for key, errors in groups.items():
        n = len(errors)
        raw_bias = median(errors)
        factor = n / (n + max(config.house_shrinkage, 0.0))
        bias = raw_bias * factor
        mae = _mean([abs(x) for x in errors])
        out[key] = (bias, mae, n)
    return out


def _house_history_stats(
    historical: Sequence[HistoricalError],
) -> dict[str, tuple[float, int]]:
    groups: dict[str, list[float]] = {}
    for row in historical:
        groups.setdefault(row.house, []).append(abs(row.estimate_pct - row.actual_pct))
    return {house: (_mean(errors), len(errors)) for house, errors in groups.items()}


def _party_history_stats(
    historical: Sequence[HistoricalError],
) -> dict[str, tuple[float, int]]:
    groups: dict[str, list[float]] = {}
    for row in historical:
        groups.setdefault(row.party, []).append(abs(row.estimate_pct - row.actual_pct))
    return {party: (_mean(errors), len(errors)) for party, errors in groups.items()}


def _history_weight(mae: float, n: int, config: AggregationConfig) -> float:
    if n < config.min_history_observations:
        return 0.5
    reliability = 1.0 / max(mae, 0.25)
    strength = n / (n + config.history_strength)
    return max(config.min_weight, reliability * strength)


def aggregate_party(
    polls: Iterable[PollEstimate],
    party: str,
    as_of: str,
    historical: Iterable[HistoricalError] = (),
    config: AggregationConfig | None = None,
) -> AggregatedParty:
    """Agrega por tamaño muestral + recencia + historial + efecto de casa.

    La fecha de corte es obligatoria para impedir pesos dependientes del futuro.
    """
    cfg = config or AggregationConfig()
    date.fromisoformat(as_of)
    current = [p for p in polls if p.party == party]
    for p in current:
        _validate_poll(p)
        age = _days(as_of, p.field_end)
        if age < 0:
            raise ValueError(f"{p.poll_id}: field_end posterior a as_of")
    current = [p for p in current if _days(as_of, p.field_end) <= cfg.max_days_old]
    if not current:
        raise ValueError(f"sin encuestas utilizables para {party}")

    hist = [h for h in historical if h.election_date < as_of and h.party == party]
    hp = _house_party_stats(hist, cfg)
    hh = _house_history_stats(hist)
    pp = _party_history_stats(hist)

    median_n = median([p.sample_size for p in current])
    counts_by_house: dict[str, int] = {}
    for p in current:
        counts_by_house[p.house] = counts_by_house.get(p.house, 0) + 1

    weighted: list[WeightedPoll] = []
    for p in current:
        age = _days(as_of, p.field_end)
        sample_component = (p.sample_size / median_n) ** cfg.sample_exponent
        recency_component = exp(-0.6931471805599453 * age / cfg.recency_half_life_days)
        bias, house_mae, house_n = hp.get((p.house, party), (0.0, 0.0, 0))
        corrected = p.estimate_pct - bias
        if house_n >= cfg.min_history_observations:
            history_component = _history_weight(house_mae, house_n, cfg)
        else:
            party_mae, party_n = pp.get(party, (0.0, 0))
            history_component = _history_weight(party_mae, party_n, cfg) if party_n else 1.0
        house_mae_all, house_n_all = hh.get(p.house, (0.0, 0))
        house_component = (
            _history_weight(house_mae_all, house_n_all, cfg)
            if house_n_all >= cfg.min_history_observations else 1.0
        )
        repetition_component = cfg.repeated_house_penalty ** max(0, counts_by_house[p.house] - 1)
        weight = max(
            cfg.min_weight,
            sample_component * recency_component * history_component
            * house_component * repetition_component,
        )
        weighted.append(WeightedPoll(
            p.poll_id, p.house, p.party, p.estimate_pct, corrected, weight,
            sample_component, recency_component, history_component,
            house_component, repetition_component, age,
        ))

    total_w = sum(x.weight for x in weighted)
    if total_w <= 0:
        raise ValueError("pesos nulos")
    estimate = sum(x.corrected_estimate_pct * x.weight for x in weighted) / total_w
    residuals = [x.corrected_estimate_pct - estimate for x in weighted]
    spread = _quantile([abs(x) for x in residuals], 0.80) if residuals else 0.0
    return AggregatedParty(
        party=party,
        estimate_pct=estimate,
        lower_bound_pct=max(0.0, estimate - spread),
        upper_bound_pct=min(100.0, estimate + spread),
        effective_polls=(total_w ** 2) / sum(x.weight ** 2 for x in weighted),
        weighted_observations=tuple(weighted),
    )


def aggregate_all(
    polls: Iterable[PollEstimate],
    as_of: str,
    historical: Iterable[HistoricalError] = (),
    config: AggregationConfig | None = None,
) -> dict[str, AggregatedParty]:
    rows = list(polls)
    return {
        p: aggregate_party(rows, p, as_of, historical=historical, config=config)
        for p in sorted({x.party for x in rows})
    }


def to_audit_dict(result: AggregatedParty) -> dict:
    payload = asdict(result)
    payload["weighted_observations"] = [asdict(x) for x in result.weighted_observations]
    return payload
