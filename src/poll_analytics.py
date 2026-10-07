"""Analytics reproducibles sobre encuestas ya validadas; sin completar datos ausentes."""
from __future__ import annotations
from collections import defaultdict
from statistics import median
from typing import Iterable
from .poll_monitor import Poll


def aggregate(polls: Iterable[Poll]) -> dict[str, float]:
    rows=list(polls)
    if not rows:
        raise ValueError("No hay encuestas")
    parties=sorted({p for row in rows for p in row.parties})
    return {party: sum(row.parties.get(party, 0.0) for row in rows) / len(rows) for party in parties}


def time_series(polls: Iterable[Poll]) -> list[dict]:
    rows=sorted(polls, key=lambda p: (p.publication_date, p.poll_id))
    return [{"date": r.publication_date, "poll_id": r.poll_id, "pollster": r.pollster,
             "parties": dict(sorted(r.parties.items()))} for r in rows]


def by_pollster(polls: Iterable[Poll]) -> dict[str, dict[str, float]]:
    grouped=defaultdict(list)
    for row in polls:
        grouped[row.pollster].append(row)
    return {house: aggregate(rows) for house, rows in sorted(grouped.items())}


def detect_anomalies(polls: Iterable[Poll], z: float = 2.5) -> list[dict]:
    rows=list(polls)
    if len(rows) < 3:
        return []
    parties=sorted({p for row in rows for p in row.parties})
    out=[]
    for party in parties:
        values=[row.parties[party] for row in rows if party in row.parties]
        if len(values)<3:
            continue
        med=median(values)
        deviations=[abs(v-med) for v in values]
        mad=median(deviations)
        scale=1.4826*mad
        if scale == 0:
            # Si toda la serie histórica coincide con la mediana, cualquier
            # desviación no nula es una anomalía inequívoca; no se puede
            # fabricar un z-score finito con MAD=0.
            for row in rows:
                if party in row.parties and row.parties[party] != med:
                    out.append({"poll_id": row.poll_id, "party": party, "value": row.parties[party],
                                "median": med, "robust_z": float("inf")})
            continue
        for row in rows:
            if party in row.parties and abs(row.parties[party]-med)/scale >= z:
                out.append({"poll_id":row.poll_id,"party":party,"value":row.parties[party],
                            "median":med,"robust_z":abs(row.parties[party]-med)/scale})
    return out


def relevant_movements(polls: Iterable[Poll], threshold: float = 2.0) -> list[dict]:
    rows=sorted(polls, key=lambda p: (p.publication_date, p.poll_id))
    out=[]
    for previous, current in zip(rows, rows[1:]):
        parties=set(previous.parties) | set(current.parties)
        for party in sorted(parties):
            if party not in previous.parties or party not in current.parties:
                continue
            delta=current.parties[party]-previous.parties[party]
            if abs(delta) >= threshold:
                out.append({"from_poll":previous.poll_id,"to_poll":current.poll_id,
                            "party":party,"delta":delta})
    return out
