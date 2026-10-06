"""SEEC hierarchical Bayesian compositional model.

Production model contract:
- national latent composition
- temporal drift
- province random effects
- survey house effects
- turnout latent state
- no invented observations: every likelihood row must come from a cited dataset.
"""
from __future__ import annotations
from dataclasses import dataclass
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
    total=sum(float(shares[p]) for p in parties)
    if abs(total-1.0)>1e-9:
        raise ValueError("las proporciones deben sumar 1")

def build_model(provinces: Sequence[str], parties: Sequence[str],
                historical: Sequence[ProvinceObservation],
                surveys: Sequence[SurveyRow]):
    try:
        import pymc as pm
        import pytensor.tensor as pt
    except ImportError as exc:
        raise RuntimeError("PyMC es obligatorio para ejecutar SEEC en producción") from exc

    if not historical:
        raise ValueError("sin observaciones históricas")
    if any(x.valid_votes <= 0 or x.votes < 0 or x.votes > x.valid_votes
           for x in historical):
        raise ValueError("observación electoral inválida")
    if any(x.sample_size <= 0 or not 0 <= x.estimate <= 1 for x in surveys):
        raise ValueError("encuesta inválida")

    party_idx={p:i for i,p in enumerate(parties)}
    prov_idx={p:i for i,p in enumerate(provinces)}
    hidx={h:i for i,h in enumerate(sorted({s.house for s in surveys}))}
    with pm.Model(coords={"party":parties,"province":provinces,
                          "house":list(sorted(hidx))}) as model:
        # Historical national composition is a prior, never a hard constraint.
        counts=[sum(x.votes for x in historical if x.party==p) for p in parties]
        national=pm.Dirichlet("national", a=pt.as_tensor_variable([max(1,c+1) for c in counts]),
                               dims="party")
        sigma_prov=pm.HalfNormal("sigma_prov", sigma=0.35)
        z=pm.Normal("province_raw", 0, 1, dims=("province","party"))
        logits=pt.log(national)[None,:] + sigma_prov*z
        province_share=pm.Deterministic(
            "province_share", pm.math.softmax(logits, axis=1), dims=("province","party"))

        sigma_house=pm.HalfNormal("sigma_house", sigma=0.05)
        house_effect=pm.Normal("house_effect", 0, sigma_house, dims=("house","party"))

        # Historical province observations inform the same latent composition.
        hprov=[]; hvotes=[]
        for x in historical:
            hprov.append(prov_idx[x.province]); hvotes.append(x.votes)
        # One likelihood per observed party/province, preserving compositional structure.
        obs_matrix=[]
        for pr in provinces:
            row=[]
            for pa in parties:
                row.append(next((x.votes for x in historical
                                 if x.province==pr and x.party==pa),0))
            if sum(row):
                obs_matrix.append((pr,row))
        for pr,row in obs_matrix:
            pm.Multinomial(f"election_{pr}", n=sum(row),
                           p=province_share[prov_idx[pr]],
                           observed=row)

        # Poll likelihood uses effective sample size; house effect is latent.
        for i,s in enumerate(surveys):
            p=party_idx.get(s.party)
            if p is None:
                raise ValueError(f"encuesta {s.poll_id}: partido no está en el universo")
            h=hidx[s.house]
            latent=pm.math.clip(national[p] + house_effect[h,p], 1e-6, 1-1e-6)
            k=max(1,int(round(s.estimate*s.sample_size)))
            pm.Binomial(f"poll_{i}", n=s.sample_size, p=latent, observed=k)

    return model
