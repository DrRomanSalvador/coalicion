"""SEEC hierarchical Bayesian compositional model.

Production model contract:
- national latent composition with an exogenous prior
- historical electoral evidence enters once through the election likelihood
- temporal drift between survey field dates
- province random effects around the national baseline
- survey-house effects expressed compositionally
- survey likelihood is multinomial at poll level
- fail closed when published survey rows are not a complete composition
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Mapping, Sequence


@dataclass(frozen=True)
class SurveyRow:
    poll_id: str
    field_date: str
    house: str
    party: str
    estimate: float
    sample_size: int
    population: str = "national"


@dataclass(frozen=True)
class ProvinceObservation:
    election: str
    province: str
    party: str
    votes: int
    valid_votes: int
    turnout: float


def validate_composition(parties: Sequence[str], shares: Mapping[str, float]) -> None:
    if not parties or set(parties) != set(shares):
        raise ValueError("composición de partidos inconsistente")
    if any(v < 0 for v in shares.values()):
        raise ValueError("proporción negativa")
    total = sum(float(shares[p]) for p in parties)
    if abs(total - 1.0) > 1e-9:
        raise ValueError("las proporciones deben sumar 1")


def _survey_counts(
    parties: Sequence[str], rows: Sequence[SurveyRow]
) -> tuple[list[int], int]:
    """Reconstruct integer counts from published shares using largest remainder.

    SurveyRow does not contain raw respondent counts. The only defensible
    reconstruction is deterministic rounding that preserves the published
    composition and the declared sample size. Incomplete compositions fail
    closed rather than silently treating omitted parties as zero.
    """
    if not rows:
        raise ValueError("encuesta sin filas")

    sample_sizes = {r.sample_size for r in rows}
    if len(sample_sizes) != 1:
        raise ValueError("una encuesta debe tener un único tamaño muestral")

    shares = {r.party: float(r.estimate) for r in rows}
    if set(shares) != set(parties):
        raise ValueError(
            f"encuesta {rows[0].poll_id}: debe contener exactamente todos los partidos"
        )
    validate_composition(parties, shares)

    n = rows[0].sample_size
    raw = [shares[p] * n for p in parties]
    counts = [int(x) for x in raw]
    remaining = n - sum(counts)
    order = sorted(
        range(len(parties)),
        key=lambda i: (raw[i] - counts[i], parties[i]),
        reverse=True,
    )
    for i in order[:remaining]:
        counts[i] += 1
    if sum(counts) != n:
        raise RuntimeError("reconstrucción multinomial inconsistente")
    return counts, n


def build_model(
    provinces: Sequence[str],
    parties: Sequence[str],
    historical: Sequence[ProvinceObservation],
    surveys: Sequence[SurveyRow],
):
    try:
        import pymc as pm
        import pytensor.tensor as pt
    except ImportError as exc:
        raise RuntimeError(
            "PyMC es obligatorio para ejecutar SEEC en producción"
        ) from exc

    if not provinces or not parties:
        raise ValueError("provincias y partidos son obligatorios")
    if not historical:
        raise ValueError("sin observaciones históricas")
    if any(
        x.valid_votes <= 0
        or x.votes < 0
        or x.votes > x.valid_votes
        for x in historical
    ):
        raise ValueError("observación electoral inválida")
    if any(x.sample_size <= 0 or not 0 <= x.estimate <= 1 for x in surveys):
        raise ValueError("encuesta inválida")

    party_idx = {p: i for i, p in enumerate(parties)}
    prov_idx = {p: i for i, p in enumerate(provinces)}
    if any(x.party not in party_idx for x in historical):
        raise ValueError("observación histórica con partido fuera del universo")
    if any(x.province not in prov_idx for x in historical):
        raise ValueError("observación histórica con provincia fuera del universo")

    polls: dict[str, list[SurveyRow]] = {}
    for row in surveys:
        if row.party not in party_idx:
            raise ValueError(
                f"encuesta {row.poll_id}: partido no está en el universo"
            )
        try:
            date.fromisoformat(row.field_date)
        except ValueError as exc:
            raise ValueError(
                f"encuesta {row.poll_id}: field_date inválida"
            ) from exc
        polls.setdefault(row.poll_id, []).append(row)

    poll_dates = sorted({rows[0].field_date for rows in polls.values()})
    if any(len({r.field_date for r in rows}) != 1 for rows in polls.values()):
        raise ValueError("una encuesta debe tener una única field_date")
    for poll_id, rows in polls.items():
        if len({r.house for r in rows}) != 1:
            raise ValueError(f"encuesta {poll_id}: debe tener una única casa")
        _survey_counts(parties, rows)

    houses = sorted({s.house for s in surveys})
    with pm.Model(
        coords={
            "party": parties,
            "province": provinces,
            "house": houses,
            "time": poll_dates,
        }
    ) as model:
        # Exogenous structural prior: historical observations do NOT enter
        # these hyperparameters. Historical evidence is consumed exactly once
        # below by the province-level multinomial likelihoods.
        national_0 = pm.Dirichlet(
            "national_0",
            a=pt.ones(len(parties)),
            dims="party",
        )

        # Static province effects are centered on the national baseline.
        sigma_prov = pm.HalfNormal("sigma_prov", sigma=0.35)
        province_raw = pm.Normal(
            "province_raw",
            0,
            1,
            dims=("province", "party"),
        )
        province_logits = (
            pt.log(national_0)[None, :]
            + sigma_prov * (
                province_raw - pt.mean(province_raw, axis=1, keepdims=True)
            )
        )
        province_share = pm.Deterministic(
            "province_share",
            pm.math.softmax(province_logits, axis=1),
            dims=("province", "party"),
        )

        # Historical electoral evidence: one compositional likelihood per
        # province. No historical count is reused as a prior parameter.
        for pr in provinces:
            row = [
                sum(
                    x.votes
                    for x in historical
                    if x.province == pr and x.party == pa
                )
                for pa in parties
            ]
            if sum(row):
                pm.Multinomial(
                    f"election_{pr}",
                    n=sum(row),
                    p=province_share[prov_idx[pr]],
                    observed=row,
                )

        # Dynamic national composition on log-ratio coordinates. The
        # increments are shared across parties and centered so the softmax is
        # identifiable; field_date now determines which latent state each poll
        # observes.
        n_times = len(poll_dates)
        if n_times:
            drift_sigma = pm.HalfNormal("drift_sigma", sigma=0.05)
            innovations = pm.Normal(
                "national_drift",
                0,
                drift_sigma,
                dims=("time", "party"),
            )
            centered_innovations = innovations - pt.mean(
                innovations, axis=1, keepdims=True
            )
            eta = pt.log(national_0)[None, :] + pt.cumsum(
                centered_innovations, axis=0
            )
            national_t = pm.Deterministic(
                "national_t",
                pm.math.softmax(eta, axis=1),
                dims=("time", "party"),
            )
        else:
            national_t = None

        # House effects are compositional: they perturb log-probabilities and
        # are normalized jointly, rather than adding independent probabilities.
        sigma_house = pm.HalfNormal("sigma_house", sigma=0.05)
        house_raw = pm.Normal(
            "house_raw",
            0,
            sigma_house,
            dims=("house", "party"),
        )
        house_effect = pm.Deterministic(
            "house_effect",
            house_raw - pt.mean(house_raw, axis=1, keepdims=True),
            dims=("house", "party"),
        )
        time_idx = {d: i for i, d in enumerate(poll_dates)}
        house_idx = {h: i for i, h in enumerate(houses)}

        for poll_id, rows in polls.items():
            counts, n = _survey_counts(parties, rows)
            t = time_idx[rows[0].field_date]
            h = house_idx[rows[0].house]
            logits = pt.log(national_t[t]) + house_effect[h]
            p = pm.Deterministic(
                f"poll_share_{poll_id}",
                pm.math.softmax(logits),
            )
            pm.Multinomial(
                f"poll_{poll_id}",
                n=n,
                p=p,
                observed=counts,
            )

    return model
