"""Monte Carlo reproducible: el sampler contiene explícitamente los supuestos."""
from __future__ import annotations
from dataclasses import dataclass
from math import floor
import numpy as np
from statistics import mean
from .reproducibility_contract import ExecutionContract

CANONICAL_SEED = ExecutionContract.seed
CANONICAL_RNG = ExecutionContract.rng
@dataclass(frozen=True)
class SimulationConfig:
    iterations:int=10000
    seed:int=CANONICAL_SEED
    rng_algorithm:str=CANONICAL_RNG
    version:str="seec-mc-1"
@dataclass(frozen=True)
class SimulationResult:
    p10:dict[str,float]; p50:dict[str,float]; p90:dict[str,float]
    probabilities:dict[str,float]; iterations:int; seed:int; rng_algorithm:str; version:str
def _q(xs,q):
    ys=sorted(xs); pos=(len(ys)-1)*q; lo=floor(pos); hi=min(lo+1,len(ys)-1)
    return ys[lo]+(ys[hi]-ys[lo])*(pos-lo)
def run_monte_carlo(sampler,seats_by_constituency,blank_votes_by_constituency,special_by_constituency,config):
    if isinstance(config.iterations,bool) or not isinstance(config.iterations,int) or config.iterations<10000:
        raise ValueError("se requieren al menos 10.000 simulaciones enteras")
    if isinstance(config.seed,bool) or not isinstance(config.seed,int) or config.seed<0:
        raise ValueError("semilla de simulación inválida")
    if config.rng_algorithm != CANONICAL_RNG:
        raise ValueError(f"algoritmo RNG no implementado: {config.rng_algorithm!r}; se requiere {CANONICAL_RNG}")
    if set(blank_votes_by_constituency) != set(seats_by_constituency):
        raise ValueError("los votos en blanco deben estar materializados para cada circunscripción")
    special_by_constituency = special_by_constituency or {}
    if set(special_by_constituency) - set(seats_by_constituency):
        raise ValueError("hay circunscripciones especiales fuera de la matriz")
    for special in ("Ceuta", "Melilla"):
        if special in seats_by_constituency and special_by_constituency.get(special) != special:
            raise ValueError(f"{special} debe usar su regla legal de mayoría simple")
    for constituency, special in special_by_constituency.items():
        if special in {"Ceuta", "Melilla"} and constituency != special:
            raise ValueError(f"la regla especial {special} no puede aplicarse a {constituency}")
    rng=np.random.Generator(np.random.PCG64(config.seed)); draws=[]
    for _ in range(config.iterations):
        scenario=sampler(rng); national={}
        if set(scenario)!=set(seats_by_constituency): raise ValueError("escenario territorial incompleto")
        for c,votes in scenario.items():
            vv=sum(votes.values())+blank_votes_by_constituency[c]
            from .electoral import allocate
            a=allocate(votes,seats_by_constituency[c],vv,special_by_constituency.get(c,""),blank_votes_by_constituency[c])
            if a.status!="OK": raise RuntimeError(f"simulación bloqueada: {c}: {a.status}")
            for p,s in a.seats.items(): national[p]=national.get(p,0)+s
        if sum(national.values())!=sum(seats_by_constituency.values()): raise AssertionError("escaños no conservados")
        draws.append(national)
    parties=sorted({p for d in draws for p in d})
    return SimulationResult(
        {p:_q([d.get(p,0) for d in draws],.10) for p in parties},
        {p:_q([d.get(p,0) for d in draws],.50) for p in parties},
        {p:_q([d.get(p,0) for d in draws],.90) for p in parties},
        {p:mean(d.get(p,0)>=1 for d in draws) for p in parties},
        config.iterations,config.seed,config.rng_algorithm,config.version)
