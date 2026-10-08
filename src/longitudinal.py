"""Descriptive longitudinal electoral analytics; never implies causality."""
from __future__ import annotations
from math import sqrt
from statistics import mean, pstdev
from typing import Iterable, Mapping


def series(polls: Iterable[Mapping], party: str) -> list[tuple[str, float]]:
    out=[]
    for poll in polls:
        values=poll.get("parties") if isinstance(poll.get("parties"),dict) else {}
        if party in values:
            try: out.append((str(poll.get("publication_date","")),float(values[party])))
            except (TypeError,ValueError): pass
    return sorted(out)


def moving_average(values: list[float], window: int) -> list[float]:
    if window < 1: raise ValueError("window must be positive")
    return [mean(values[max(0,i-window+1):i+1]) for i in range(len(values))]


def slope(values: list[float]) -> float | None:
    n=len(values)
    if n<2: return None
    x=range(n); xm=(n-1)/2; ym=mean(values)
    den=sum((i-xm)**2 for i in x)
    return sum((i-xm)*(y-ym) for i,y in enumerate(values))/den if den else 0.0


def volatility(values: list[float]) -> float | None:
    return pstdev(values) if values else None


def zscore_outliers(values: list[float], threshold: float=2.5) -> list[int]:
    if len(values)<3: return []
    sd=pstdev(values)
    if sd==0: return []
    m=mean(values)
    return [i for i,v in enumerate(values) if abs((v-m)/sd)>threshold]


def correlation(a: list[float], b: list[float]) -> float | None:
    if len(a)!=len(b) or len(a)<2: return None
    ma,mb=mean(a),mean(b)
    da=sqrt(sum((x-ma)**2 for x in a)); db=sqrt(sum((y-mb)**2 for y in b))
    if not (da and db): return None
    value=sum((x-ma)*(y-mb) for x,y in zip(a,b))/(da*db)
    return max(-1.0, min(1.0, value))
